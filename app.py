"""
Score Composer — Local Flask server
Run: python3 app.py
Then open: http://localhost:5000
"""

import os, json, subprocess, tempfile, threading, time, math
from pathlib import Path
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import requests as req

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

BASE    = Path(__file__).parent
UPLOADS = BASE / 'uploads'
OUTPUTS = BASE / 'outputs'
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

def out(stem):
    """Return (and create) the outputs/{stem}/ directory for a video."""
    d = OUTPUTS / stem
    d.mkdir(parents=True, exist_ok=True)
    return d

API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
EL_BASE = 'https://api.elevenlabs.io/v1'

# Music generation providers
MUSIC_PROVIDER  = os.getenv('MUSIC_PROVIDER', 'elevenlabs')   # elevenlabs | replicate | huggingface
REPLICATE_KEY   = os.getenv('REPLICATE_API_KEY', '')
HF_KEY          = os.getenv('HF_API_KEY', '')

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

# ── List video files ──────────────────────────────────────────────────────
@app.route('/api/files')
def list_files():
    videos = [f.name for f in UPLOADS.glob('*') if f.suffix.lower() in ('.mp4','.mov','.webm','.mkv','.avi')]
    return jsonify({'videos': videos})

# ── Analyze video: ffprobe metadata ──────────────────────────────────────
@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    name = data.get('filename', '')
    video = UPLOADS / name
    if not video.exists(): video = BASE / name   # fallback
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

# ── Shot detection (shared helper) ───────────────────────────────────────
def _detect_shots(video_path, threshold=0.35):
    result = subprocess.run([
        'ffmpeg', '-i', str(video_path),
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
    deduped = []
    for t in sorted(shots):
        if not deduped or t - deduped[-1] > 0.5:
            deduped.append(t)
    return deduped

@app.route('/api/shots', methods=['POST'])
def detect_shots():
    data = request.json
    name = data.get('filename', '')
    video = UPLOADS / name
    if not video.exists(): video = BASE / name
    threshold = float(data.get('threshold', 0.35))
    if not video.exists():
        return jsonify({'error': 'File not found'}), 404
    deduped = _detect_shots(video, threshold)
    stem = video.stem
    (out(stem) / 'shots.json').write_text(json.dumps({'shots': deduped, 'count': len(deduped)}, indent=2))
    return jsonify({'shots': deduped, 'count': len(deduped)})

# ── Upload video file ─────────────────────────────────────────────────────
@app.route('/api/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'No filename'}), 400
    safe_name = Path(f.filename).name
    allowed = ('.mp4', '.mov', '.webm', '.mkv', '.avi', '.mp3', '.m4a', '.wav', '.aac', '.flac')
    if not safe_name.lower().endswith(allowed):
        return jsonify({'error': 'Invalid file type — use mp4, mov, webm, mkv, mp3, m4a or wav'}), 400
    dest = UPLOADS / safe_name
    f.save(str(dest))
    return jsonify({'filename': safe_name, 'size_mb': round(dest.stat().st_size / 1e6, 1)})

# ── Full analysis pipeline (shots + cues + automation + transcript) ───────
@app.route('/api/analyze-full', methods=['POST'])
def analyze_full():
    data = request.json
    filename = data.get('filename', '')
    video = UPLOADS / filename
    if not video.exists(): video = BASE / filename   # fallback for legacy paths
    if not video.exists():
        return jsonify({'error': 'File not found'}), 404

    stem = video.stem
    od   = out(stem)   # outputs/{stem}/
    result = {}

    # 1. Duration
    try:
        r = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(video)
        ], capture_output=True, text=True)
        result['duration'] = float(json.loads(r.stdout)['format']['duration'])
    except Exception:
        result['duration'] = 0

    # 2. Shots — detect fresh if missing
    shots_f = od / 'shots.json'
    if shots_f.exists():
        result['shots'] = json.loads(shots_f.read_text()).get('shots', [])
    else:
        shots = _detect_shots(video)
        shots_f.write_text(json.dumps({'shots': shots, 'count': len(shots)}, indent=2))
        result['shots'] = shots

    # 3. Cue sheet
    cues_f = od / 'cues.json'
    result['cues'] = json.loads(cues_f.read_text()) if cues_f.exists() else []

    # 4. Volume automation
    auto_f = od / 'automation.json'
    result['automation'] = json.loads(auto_f.read_text()) if auto_f.exists() else []

    # 5. Transcript
    tr_f = od / 'transcript.json'
    result['transcript'] = json.loads(tr_f.read_text()).get('segments', []) if tr_f.exists() else []

    return jsonify(result)

# ── Load JSON from outputs/{stem}/ ───────────────────────────────────────
@app.route('/api/load/<stem>/<filename>')
def load_json(stem, filename):
    safe_stem = Path(stem).name
    safe_file = Path(filename).name
    if not safe_file.endswith('.json'):
        return jsonify({'error': 'Not a JSON file'}), 400
    f = OUTPUTS / safe_stem / safe_file
    if not f.exists():
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

# ── Music generation helpers ──────────────────────────────────────────────

def _gen_clip_replicate(prompt, duration_sec, out_path):
    """Generate one music clip via Replicate MusicGen."""
    import replicate
    # MusicGen stereo-large on Replicate
    output = replicate.run(
        "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb",
        input={
            "prompt": prompt,
            "model_version": "stereo-large",
            "output_format": "mp3",
            "normalization_strategy": "peak",
            "duration": min(int(math.ceil(duration_sec)), 30),  # MusicGen max 30s per call
        }
    )
    # output is a URL string
    audio_bytes = req.get(str(output), timeout=60).content
    out_path.write_bytes(audio_bytes)

def _gen_clip_huggingface(prompt, duration_sec, out_path):
    """Generate one music clip via HuggingFace Inference API (free tier)."""
    model = "facebook/musicgen-medium"
    api_url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {HF_KEY}"} if HF_KEY else {}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": int(duration_sec * 50)}  # ~50 tokens/sec
    }
    r = req.post(api_url, headers=headers, json=payload, timeout=120)
    if not r.ok:
        raise Exception(f"HuggingFace error {r.status_code}: {r.text[:200]}")
    out_path.write_bytes(r.content)

def _gen_clip_elevenlabs(prompt, duration_sec, out_path):
    """Generate one music clip via ElevenLabs sound-generation."""
    payload = {
        "text": prompt,
        "duration_seconds": min(duration_sec, 22),  # EL sound-gen max
        "prompt_influence": 0.5
    }
    r = req.post(f'{EL_BASE}/sound-generation',
                 json=payload,
                 headers={'xi-api-key': API_KEY, 'Content-Type': 'application/json'},
                 timeout=60, stream=True)
    if not r.ok:
        raise Exception(f"ElevenLabs error: {r.text[:200]}")
    with open(out_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk: f.write(chunk)

def _concat_clips(clip_paths, output_path):
    """Concatenate MP3 clips with 1s crossfade using ffmpeg."""
    if len(clip_paths) == 1:
        import shutil; shutil.copy(clip_paths[0], output_path)
        return
    # Build ffmpeg filter for crossfade concat
    inputs = []
    for p in clip_paths:
        inputs += ['-i', str(p)]
    # acrossfade chain
    n = len(clip_paths)
    filter_parts = []
    prev = '[0:a]'
    for i in range(1, n):
        tag = f'[cf{i}]' if i < n - 1 else ''
        filter_parts.append(f'{prev}[{i}:a]acrossfade=d=1:c1=tri:c2=tri{tag}')
        prev = tag if tag else ''
    cmd = ['ffmpeg', '-y'] + inputs + [
        '-filter_complex', ';'.join(filter_parts),
        '-c:a', 'libmp3lame', '-q:a', '4',
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise Exception(f"ffmpeg concat failed: {result.stderr[-300:]}")

# ── Unified music generation endpoint ─────────────────────────────────────
@app.route('/api/music/generate', methods=['POST'])
def music_generate():
    """
    Provider-agnostic music generation.
    Accepts same sections format as /api/el/generate.
    Dispatches to: elevenlabs | replicate | huggingface based on MUSIC_PROVIDER env.
    """
    load_dotenv(override=True)
    provider    = os.getenv('MUSIC_PROVIDER', 'elevenlabs')
    data        = request.json
    sections    = data.get('sections', [])
    stem        = data.get('stem', '')   # video stem for output directory

    if not sections:
        return jsonify({'error': 'No sections provided'}), 400

    # Output goes into outputs/{stem}/score.mp3 if stem provided, else BASE
    out_path = (out(stem) / 'score.mp3') if stem else (BASE / 'score.mp3')

    # ElevenLabs compose-detailed handles sections natively
    if provider == 'elevenlabs':
        if not os.getenv('ELEVENLABS_API_KEY', ''):
            return jsonify({'error': 'No ElevenLabs API key — add it in Settings'}), 400
        payload = {'sections': sections, 'output_format': 'mp3_44100_128'}
        r = req.post(f'{EL_BASE}/music/compose-detailed',
                     json=payload,
                     headers={'xi-api-key': os.getenv('ELEVENLABS_API_KEY'), 'Content-Type': 'application/json'},
                     timeout=300, stream=True)
        if not r.ok:
            return jsonify({'error': r.text, 'status': r.status_code}), r.status_code
        with open(out_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)
        return jsonify({'success': True, 'file': 'score.mp3', 'stem': stem,
                        'size_mb': round(out_path.stat().st_size / 1e6, 2),
                        'provider': 'elevenlabs'})

    # Replicate / HuggingFace: generate per section, then concat
    if provider == 'replicate' and not os.getenv('REPLICATE_API_KEY', ''):
        return jsonify({'error': 'No Replicate API key — add it in Settings'}), 400

    tmp_dir = Path(tempfile.mkdtemp())
    clip_paths = []
    try:
        for i, sec in enumerate(sections):
            prompt   = sec.get('prompt', 'Cinematic orchestral background music')
            t0       = float(sec.get('start_time_seconds', 0))
            t1       = float(sec.get('end_time_seconds', t0 + 30))
            duration = max(5, t1 - t0)
            clip_out = tmp_dir / f'clip_{i:03d}.mp3'

            # For long sections, generate in 30s chunks and concat
            if duration <= 30:
                if provider == 'replicate':
                    _gen_clip_replicate(prompt, duration, clip_out)
                else:
                    _gen_clip_huggingface(prompt, duration, clip_out)
                clip_paths.append(clip_out)
            else:
                # Split into 28s chunks with 1s overlap for crossfade
                sub_clips = []
                pos = 0
                chunk_idx = 0
                while pos < duration:
                    chunk_len = min(28, duration - pos)
                    if chunk_len < 3: break
                    sub_out = tmp_dir / f'clip_{i:03d}_sub{chunk_idx:02d}.mp3'
                    if provider == 'replicate':
                        _gen_clip_replicate(prompt, chunk_len, sub_out)
                    else:
                        _gen_clip_huggingface(prompt, chunk_len, sub_out)
                    sub_clips.append(sub_out)
                    pos += 27   # 1s overlap
                    chunk_idx += 1
                if len(sub_clips) == 1:
                    clip_paths.append(sub_clips[0])
                else:
                    merged = tmp_dir / f'clip_{i:03d}_merged.mp3'
                    _concat_clips(sub_clips, merged)
                    clip_paths.append(merged)

        _concat_clips(clip_paths, out_path)
        return jsonify({'success': True, 'file': 'score.mp3', 'stem': stem,
                        'size_mb': round(out_path.stat().st_size / 1e6, 2),
                        'provider': provider})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

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
@app.route('/api/download/<stem>/<filename>')
def download(stem, filename):
    safe_stem = Path(stem).name
    safe_file = Path(filename).name
    # Search outputs/{stem}/, then uploads/, then BASE
    for search_dir in [OUTPUTS / safe_stem, UPLOADS, BASE]:
        f = search_dir / safe_file
        if f.exists():
            return send_file(f, as_attachment=True)
    return jsonify({'error': 'Not found'}), 404

# ── Run Whisper transcription (async-ish via thread) ─────────────────────
transcription_status = {}

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    data = request.json
    name = data.get('filename', '')
    video = UPLOADS / name
    if not video.exists(): video = BASE / name
    language = data.get('language', 'en')
    model    = data.get('model', 'medium')
    job_id   = str(int(time.time()))

    if not video.exists():
        return jsonify({'error': 'File not found'}), 404

    transcription_status[job_id] = {'status': 'running', 'progress': 0}
    stem = video.stem

    def run():
        try:
            # Extract audio to a temp file inside outputs/{stem}/
            od  = out(stem)
            wav = od / 'audio_extracted.wav'
            subprocess.run([
                'ffmpeg', '-i', str(video), '-vn',
                '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                str(wav), '-y'
            ], capture_output=True, check=True)

            transcription_status[job_id]['progress'] = 30

            result = subprocess.run([
                'python3', '-m', 'whisper', str(wav),
                '--model', model, '--language', language,
                '--output_format', 'json', '--output_dir', str(od)
            ], capture_output=True, text=True, timeout=600)

            transcription_status[job_id]['progress'] = 90

            raw = od / 'audio_extracted.json'
            if raw.exists():
                data_raw = json.loads(raw.read_text())
                segments = [{
                    'id': s['id'], 'start': round(s['start'], 2),
                    'end': round(s['end'], 2),
                    'start_fmt': f"{int(s['start']//60)}:{int(s['start']%60):02d}",
                    'text': s['text'].strip()
                } for s in data_raw['segments']]
                (od / 'transcript.json').write_text(
                    json.dumps({'source': video.name, 'language': language,
                                'model': model, 'segments': segments},
                               indent=2, ensure_ascii=False))
                raw.unlink(missing_ok=True)   # clean up temp whisper json
            wav.unlink(missing_ok=True)        # clean up extracted wav

            transcription_status[job_id] = {'status': 'done', 'progress': 100}
        except Exception as e:
            transcription_status[job_id] = {'status': 'error', 'error': str(e)}

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'job_id': job_id})

@app.route('/api/transcribe/status/<job_id>')
def transcribe_status(job_id):
    return jsonify(transcription_status.get(job_id, {'status': 'unknown'}))

# ── Setup status (what keys are configured) ──────────────────────────────
@app.route('/api/setup-status')
def setup_status():
    load_dotenv(override=True)
    music_provider = os.getenv('MUSIC_PROVIDER', 'elevenlabs')
    music_ready = {
        'elevenlabs': bool(os.getenv('ELEVENLABS_API_KEY', '')),
        'replicate':  bool(os.getenv('REPLICATE_API_KEY', '')),
        'huggingface': True,   # free tier works without a key
    }.get(music_provider, False)
    llm_key = bool(os.getenv('LLM_API_KEY', '') or os.getenv('LLM_PROVIDER', '') == 'ollama')
    return jsonify({
        'el_configured':     bool(os.getenv('ELEVENLABS_API_KEY', '')),
        'music_configured':  music_ready,
        'music_provider':    music_provider,
        'llm_configured':    llm_key,
        'llm_provider':      os.getenv('LLM_PROVIDER', ''),
        'ready':             music_ready and llm_key
    })

# ── Build voice-duck automation curve from transcript ─────────────────────
@app.route('/api/build-automation', methods=['POST'])
def build_automation():
    """
    Takes transcript segments and a video duration, returns a keyframe list
    [[time, volume], ...] that ducks music under speech and raises it during silences.
    Also saves as {stem}_automation.json so future runs skip this step.
    """
    data       = request.json
    segments   = data.get('segments', [])   # [{start, end, ...}, ...]
    duration   = float(data.get('duration', 0))
    stem       = data.get('stem', '')

    HIGH   = 0.90   # music volume during silence
    LOW    = 0.12   # music volume under speech
    FADE   = 0.4    # seconds to ramp in/out

    if not segments or duration == 0:
        # No speech data — flat curve at high volume
        kf = [[0, HIGH], [duration, HIGH]]
        if stem:
            (out(stem) / 'automation.json').write_text(json.dumps(kf))
        return jsonify({'automation': kf, 'keyframes': len(kf)})

    events = []  # (time, vol)
    for seg in segments:
        t0 = float(seg.get('start', 0))
        t1 = float(seg.get('end', t0))
        # Fade down before speech starts
        events.append((max(0, t0 - FADE), HIGH))
        events.append((t0, LOW))
        # Fade up after speech ends
        events.append((t1, LOW))
        events.append((min(duration, t1 + FADE), HIGH))

    # Sort and deduplicate (keep last value at same time)
    events.sort(key=lambda x: x[0])
    kf = [[0, HIGH]]
    for t, v in events:
        if kf and abs(t - kf[-1][0]) < 0.05:
            kf[-1][1] = v  # overwrite same-time event
        else:
            kf.append([round(t, 3), v])
    if kf[-1][0] < duration:
        kf.append([round(duration, 3), HIGH])

    if stem:
        (out(stem) / 'automation.json').write_text(json.dumps(kf))

    return jsonify({'automation': kf, 'keyframes': len(kf)})

# ── Mix video + generated score into one file ─────────────────────────────
@app.route('/api/mix-video', methods=['POST'])
def mix_video():
    data        = request.json
    video_name  = data.get('video', '')
    audio_name  = data.get('audio', 'score.mp3')
    automation  = data.get('automation', [])
    master      = float(data.get('master_level', 0.28))
    stem        = Path(video_name).stem
    od          = out(stem)

    video_path  = UPLOADS / video_name
    if not video_path.exists(): video_path = BASE / video_name

    # Audio may be just a filename — search outputs/{stem}/ first
    audio_path = od / Path(audio_name).name
    if not audio_path.exists(): audio_path = OUTPUTS / Path(audio_name).name
    if not audio_path.exists(): audio_path = BASE / audio_name

    output_path = od / 'scored.mp4'

    if not video_path.exists():
        return jsonify({'error': f'Video not found: {video_name}'}), 404
    if not audio_path.exists():
        return jsonify({'error': f'Audio not found: {audio_name}'}), 404

    # Build ffmpeg volume expression from automation keyframes
    def vol_expr(kf, master):
        if len(kf) < 2:
            return str(master)
        parts = []
        for i in range(len(kf) - 1):
            t0, v0 = kf[i]
            t1, v1 = kf[i + 1]
            slope = (v1 - v0) / (t1 - t0) if t1 != t0 else 0
            parts.append(
                f"between(t,{t0},{t1})*({v0:.4f}+{slope:.6f}*(t-{t0}))*{master}"
            )
        # After last keyframe: hold final value
        parts.append(f"gte(t,{kf[-1][0]})*{kf[-1][1]*master:.4f}")
        return '+'.join(parts)

    if automation:
        vol_filter = f"[1:a]volume=eval=frame:volume='{vol_expr(automation, master)}'[music]"
    else:
        vol_filter = f"[1:a]volume={master}[music]"

    cmd = [
        'ffmpeg', '-y',
        '-i', str(video_path),
        '-i', str(audio_path),
        '-filter_complex',
        f'{vol_filter};[0:a][music]amix=inputs=2:duration=first:dropout_transition=2',
        '-map', '0:v', '-c:v', 'copy',
        '-shortest',
        str(output_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return jsonify({'error': result.stderr[-600:]}), 500
        size_mb = round(output_path.stat().st_size / 1e6, 1)
        return jsonify({'success': True, 'file': 'scored.mp4', 'stem': stem, 'size_mb': size_mb})
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Mix timed out (video too long?)'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── LLM Settings (read/write .env securely) ──────────────────────────────
@app.route('/api/settings', methods=['GET', 'POST'])
def llm_settings():
    env_file = BASE / '.env'
    if request.method == 'GET':
        return jsonify({
            'provider':  os.getenv('LLM_PROVIDER', ''),
            'model':     os.getenv('LLM_MODEL', ''),
            'base_url':  os.getenv('LLM_BASE_URL', ''),
            'has_key':   bool(os.getenv('LLM_API_KEY', ''))
        })
    data = request.json
    existing = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, _, v = line.partition('=')
                existing[k.strip()] = v.strip()
    for field, env_key in [('provider','LLM_PROVIDER'),('model','LLM_MODEL'),
                            ('api_key','LLM_API_KEY'),('base_url','LLM_BASE_URL'),
                            ('el_key','ELEVENLABS_API_KEY'),
                            ('music_provider','MUSIC_PROVIDER'),
                            ('replicate_key','REPLICATE_API_KEY'),
                            ('hf_key','HF_API_KEY')]:
        if data.get(field):
            existing[env_key] = data[field]
    env_file.write_text('\n'.join(f'{k}={v}' for k, v in existing.items()) + '\n')
    load_dotenv(override=True)
    return jsonify({'success': True})

# ── Generate cue sheet via LLM ────────────────────────────────────────────
@app.route('/api/generate-cues', methods=['POST'])
def generate_cues():
    provider = os.getenv('LLM_PROVIDER', 'openrouter')
    model    = os.getenv('LLM_MODEL', '')
    api_key  = os.getenv('LLM_API_KEY', '')
    base_url = os.getenv('LLM_BASE_URL', '')

    if not api_key:
        return jsonify({'error': 'No LLM API key. Open Settings (⚙) and connect a provider.'}), 400

    data       = request.json
    transcript = data.get('transcript', [])
    shots      = data.get('shots', [])
    duration   = data.get('duration', 0)
    num_cues   = int(data.get('num_cues', 7))
    filename   = data.get('filename', '')

    if not transcript:
        return jsonify({'error': 'No transcript — transcribe the video first.'}), 400

    tr_text    = '\n'.join(f"[{s['start_fmt']}] {s['text']}" for s in transcript)
    shots_text = ', '.join(f"{int(t//60)}:{int(t%60):02d}" for t in shots[:25])
    dur_fmt    = f"{int(duration//60)}:{int(duration%60):02d}"

    system = ("You are a professional film score composer and music editor. "
              "You analyse video transcripts and scene data to create precise music cue sheets. "
              "Respond with valid JSON only — no markdown fences, no explanation.")

    user = f"""Create a music cue sheet with exactly {num_cues} cues for this video.

VIDEO DURATION: {dur_fmt}
SHOT CHANGES AT: {shots_text}

TRANSCRIPT:
{tr_text}

Return a JSON array of {num_cues} objects. Each must have:
- "cue": integer (1–{num_cues})
- "start": "M:SS"
- "end": "M:SS"
- "name": evocative 2–4 word title
- "suggested_mood": 3 descriptors joined with " + " (e.g. "tension + intrigue + mystery")
- "narrative_beat": one sentence — what is the narrator doing/revealing here?
- "transcript_snippet": exact 1–2 sentence quote from the transcript above
- "lyria_prompt": 2–3 sentence ElevenLabs music prompt. Include: instruments, BPM, energy, specific techniques. No vocals.

Rules: cues cover entire video with no gaps. Each cue 30–120s. Match energy to narrative tension.
Return ONLY the JSON array."""

    headers = {'Content-Type': 'application/json'}

    if provider == 'anthropic':
        headers['x-api-key'] = api_key
        headers['anthropic-version'] = '2023-06-01'
        payload = {'model': model or 'claude-opus-4-6', 'max_tokens': 4000,
                   'system': system, 'messages': [{'role':'user','content':user}]}
        url = 'https://api.anthropic.com/v1/messages'
    else:
        headers['Authorization'] = f'Bearer {api_key}'
        if provider == 'openrouter':
            headers['HTTP-Referer'] = 'https://vibosing.app'
            headers['X-Title'] = 'VIBosing'
        payload = {'model': model or 'anthropic/claude-opus-4',
                   'messages': [{'role':'system','content':system},{'role':'user','content':user}],
                   'max_tokens': 4000, 'temperature': 0.7}
        if provider == 'openrouter':
            url = 'https://openrouter.ai/api/v1/chat/completions'
        elif provider == 'ollama':
            url = (base_url or 'http://localhost:11434') + '/v1/chat/completions'
        elif base_url:
            url = base_url
        else:
            url = 'https://api.openai.com/v1/chat/completions'

    try:
        r = req.post(url, json=payload, headers=headers, timeout=120)
        if not r.ok:
            return jsonify({'error': f'LLM {r.status_code}: {r.text[:400]}'}), 500
        resp = r.json()
        content = (resp['content'][0]['text'] if provider == 'anthropic'
                   else resp['choices'][0]['message']['content']).strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        cues = json.loads(content)
        if filename:
            (out(Path(filename).stem) / 'cues.json').write_text(
                json.dumps(cues, indent=2, ensure_ascii=False))
        return jsonify({'cues': cues, 'count': len(cues)})
    except json.JSONDecodeError as e:
        return jsonify({'error': f'LLM returned invalid JSON: {e}. Try again.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('\n  Score Composer running at http://localhost:5000\n')
    app.run(host='0.0.0.0', port=5000, debug=False)
