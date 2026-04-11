"""
Score Composer — Local Flask server
Run: python3 app.py
Then open: http://localhost:5000
"""

import os, json, subprocess, tempfile, threading, time
from pathlib import Path
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import requests as req

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

BASE = Path(__file__).parent
API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
EL_BASE = 'https://api.elevenlabs.io/v1'

# ── Serve frontend ────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory(BASE, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(BASE, filename)

# ── Health / key check ────────────────────────────────────────────────────
@app.route('/api/status')
def status():
    has_key = bool(API_KEY)
    credits = None
    if has_key:
        try:
            r = req.get(f'{EL_BASE}/user', headers={'xi-api-key': API_KEY}, timeout=5)
            if r.ok:
                data = r.json()
                credits = data.get('subscription', {}).get('character_count', None)
        except Exception:
            pass
    return jsonify({'key_loaded': has_key, 'credits': credits})

# ── List video files in project folder ───────────────────────────────────
@app.route('/api/files')
def list_files():
    videos = [f.name for f in BASE.glob('*.mp4')]
    jsons  = [f.name for f in BASE.glob('*.json') if f.name not in ('package.json',)]
    return jsonify({'videos': videos, 'jsons': jsons})

# ── Analyze video: ffprobe metadata ──────────────────────────────────────
@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    video = BASE / data.get('filename', 'The_Missing_Ancestor.mp4')
    if not video.exists():
        return jsonify({'error': 'File not found'}), 404

    result = subprocess.run([
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_streams', '-show_format', str(video)
    ], capture_output=True, text=True)
    meta = json.loads(result.stdout)
    fmt = meta['format']
    return jsonify({
        'duration': float(fmt['duration']),
        'size_mb': round(int(fmt['size']) / 1e6, 1),
        'filename': video.name
    })

# ── Shot detection ────────────────────────────────────────────────────────
@app.route('/api/shots', methods=['POST'])
def detect_shots():
    data = request.json
    video = BASE / data.get('filename', 'The_Missing_Ancestor.mp4')
    threshold = float(data.get('threshold', 0.35))

    if not video.exists():
        return jsonify({'error': 'File not found'}), 404

    # Use ffmpeg scene detection
    result = subprocess.run([
        'ffmpeg', '-i', str(video),
        '-vf', f"select='gt(scene,{threshold})',showinfo",
        '-f', 'null', '-'
    ], capture_output=True, text=True, timeout=120)

    shots = []
    for line in result.stderr.split('\n'):
        if 'pts_time' in line and 'showinfo' in line:
            try:
                pts_part = [p for p in line.split() if 'pts_time' in p][0]
                t = float(pts_part.split(':')[1])
                shots.append(round(t, 2))
            except Exception:
                continue

    # Deduplicate close shots (within 0.5s)
    deduped = []
    for t in sorted(shots):
        if not deduped or t - deduped[-1] > 0.5:
            deduped.append(t)

    # Save to file
    out = BASE / 'shot_changes.json'
    out.write_text(json.dumps({'shots': deduped, 'count': len(deduped)}, indent=2))

    return jsonify({'shots': deduped, 'count': len(deduped)})

# ── Load existing JSON files ──────────────────────────────────────────────
@app.route('/api/load/<filename>')
def load_json(filename):
    safe = Path(filename).name  # prevent path traversal
    f = BASE / safe
    if not f.exists() or f.suffix != '.json':
        return jsonify({'error': 'Not found'}), 404
    return jsonify(json.loads(f.read_text()))

# ── ElevenLabs: cost preview BEFORE generating ───────────────────────────
@app.route('/api/el/preview-cost', methods=['POST'])
def preview_cost():
    """Calculate credit cost before user presses Generate."""
    if not API_KEY:
        return jsonify({'error': 'No API key in .env'}), 400

    data = request.json
    sections = data.get('sections', [])

    # ElevenLabs music: 900 credits per minute
    CREDITS_PER_MIN = 900
    total_seconds = sum(s.get('end_seconds', 0) - s.get('start_seconds', 0) for s in sections)
    total_minutes = total_seconds / 60
    credits_needed = round(total_minutes * CREDITS_PER_MIN)

    # Get current balance
    balance = None
    try:
        r = req.get(f'{EL_BASE}/user', headers={'xi-api-key': API_KEY}, timeout=5)
        if r.ok:
            u = r.json()
            sub = u.get('subscription', {})
            balance = sub.get('character_count', None)
            # ElevenLabs uses character_count for TTS but music uses separate credits
            # Try to get music-specific credit info
            music_credits = sub.get('available_music_credits', None) or sub.get('credits', None)
            if music_credits:
                balance = music_credits
    except Exception:
        pass

    can_afford = (balance is None) or (balance >= credits_needed)

    return jsonify({
        'total_seconds': round(total_seconds),
        'total_minutes': round(total_minutes, 2),
        'credits_needed': credits_needed,
        'credits_remaining': balance,
        'can_afford': can_afford,
        'warning': None if can_afford else f'Need {credits_needed} credits, have {balance}'
    })

# ── ElevenLabs: check account info ───────────────────────────────────────
@app.route('/api/el/account')
def el_account():
    if not API_KEY:
        return jsonify({'error': 'No API key in .env'}), 400
    r = req.get(f'{EL_BASE}/user', headers={'xi-api-key': API_KEY}, timeout=8)
    if not r.ok:
        return jsonify({'error': r.text}), r.status_code
    return jsonify(r.json())

# ── ElevenLabs: generate full score (compose-detailed) ───────────────────
@app.route('/api/el/generate', methods=['POST'])
def el_generate():
    if not API_KEY:
        return jsonify({'error': 'No API key in .env'}), 400

    data = request.json
    sections = data.get('sections', [])
    output_name = data.get('output', 'score_full.mp3')

    if not sections:
        return jsonify({'error': 'No sections provided'}), 400

    payload = {
        'sections': sections,
        'output_format': 'mp3_44100_128'
    }

    headers = {
        'xi-api-key': API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        r = req.post(
            f'{EL_BASE}/music/compose-detailed',
            json=payload,
            headers=headers,
            timeout=300,
            stream=True
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    if not r.ok:
        return jsonify({'error': r.text, 'status': r.status_code}), r.status_code

    # Save audio file
    out_path = BASE / output_name
    with open(out_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return jsonify({'success': True, 'file': output_name, 'size_mb': round(out_path.stat().st_size / 1e6, 2)})

# ── ElevenLabs: generate single sting (sound-generation) ─────────────────
@app.route('/api/el/sting', methods=['POST'])
def el_sting():
    if not API_KEY:
        return jsonify({'error': 'No API key in .env'}), 400

    data = request.json
    prompt = data.get('prompt', '')
    duration = float(data.get('duration_seconds', 5))
    output_name = data.get('output', 'sting.mp3')

    payload = {
        'text': prompt,
        'duration_seconds': duration,
        'prompt_influence': 0.5
    }
    headers = {'xi-api-key': API_KEY, 'Content-Type': 'application/json'}

    r = req.post(f'{EL_BASE}/sound-generation', json=payload, headers=headers, timeout=60, stream=True)
    if not r.ok:
        return jsonify({'error': r.text}), r.status_code

    out_path = BASE / output_name
    with open(out_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return jsonify({'success': True, 'file': output_name})

# ── Download any generated file ───────────────────────────────────────────
@app.route('/api/download/<filename>')
def download(filename):
    safe = Path(filename).name
    f = BASE / safe
    if not f.exists():
        return jsonify({'error': 'Not found'}), 404
    return send_file(f, as_attachment=True)

# ── Run Whisper transcription (async-ish via thread) ─────────────────────
transcription_status = {}

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    data = request.json
    video = BASE / data.get('filename', 'The_Missing_Ancestor.mp4')
    language = data.get('language', 'en')
    model = data.get('model', 'medium')
    job_id = str(int(time.time()))

    if not video.exists():
        return jsonify({'error': 'File not found'}), 404

    transcription_status[job_id] = {'status': 'running', 'progress': 0}

    def run():
        try:
            # Extract audio first
            wav = BASE / 'audio_extracted.wav'
            subprocess.run([
                'ffmpeg', '-i', str(video), '-vn',
                '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                str(wav), '-y'
            ], capture_output=True, check=True)

            transcription_status[job_id]['progress'] = 30

            # Run whisper
            result = subprocess.run([
                'python3', '-m', 'whisper', str(wav),
                '--model', model, '--language', language,
                '--output_format', 'json', '--output_dir', str(BASE)
            ], capture_output=True, text=True, timeout=600)

            transcription_status[job_id]['progress'] = 90

            # Rename output
            raw = BASE / 'audio_extracted.json'
            if raw.exists():
                data_raw = json.loads(raw.read_text())
                segments = [{
                    'id': s['id'], 'start': round(s['start'], 2),
                    'end': round(s['end'], 2),
                    'start_fmt': f"{int(s['start']//60)}:{int(s['start']%60):02d}",
                    'text': s['text'].strip()
                } for s in data_raw['segments']]
                transcript = {
                    'source': video.name, 'language': language,
                    'model': model, 'segments': segments
                }
                (BASE / 'transcript.json').write_text(json.dumps(transcript, indent=2, ensure_ascii=False))

            transcription_status[job_id] = {'status': 'done', 'progress': 100}
        except Exception as e:
            transcription_status[job_id] = {'status': 'error', 'error': str(e)}

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'job_id': job_id})

@app.route('/api/transcribe/status/<job_id>')
def transcribe_status(job_id):
    return jsonify(transcription_status.get(job_id, {'status': 'unknown'}))

# ─────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('\n  Score Composer running at http://localhost:5000\n')
    app.run(host='0.0.0.0', port=5000, debug=False)
