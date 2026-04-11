#!/usr/bin/env python3
"""
score_video.py — Music scoring pipeline for science explainer videos.

Usage:
  python3 score_video.py <video.mp4> [--language ml] [--model medium] [--cues 7]

Outputs (in same folder as video):
  transcript.json       — full timestamped Whisper transcript
  silence_gaps.json     — detected beat boundaries
  cue_sheet.json        — music cues with Lyria prompts
  lyria_prompts.txt     — ready-to-paste prompts
  capcut_edit_guide.txt — CapCut track layout

Dependencies:
  brew install ffmpeg
  pip install openai-whisper pydub
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


# ──────────────────────────────────────────────
# STEP 1: Extract audio
# ──────────────────────────────────────────────

def extract_audio(video_path: Path, out_dir: Path) -> Path:
    wav_path = out_dir / "audio_extracted.wav"
    print(f"[1/5] Extracting audio → {wav_path.name}")
    result = subprocess.run([
        "ffmpeg", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(wav_path), "-y"
    ], capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg error:", result.stderr[-500:])
        sys.exit(1)

    # Print audio metadata
    probe = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", str(wav_path)
    ], capture_output=True, text=True)
    meta = json.loads(probe.stdout)
    fmt = meta["format"]
    stream = meta["streams"][0]
    duration = float(fmt["duration"])
    print(f"    Duration: {duration:.2f}s ({duration/60:.2f} mins)")
    print(f"    Sample rate: {stream['sample_rate']} Hz  |  Channels: {stream['channels']}")
    return wav_path


# ──────────────────────────────────────────────
# STEP 2: Detect silence gaps
# ──────────────────────────────────────────────

def detect_gaps(wav_path: Path, out_dir: Path) -> list:
    from pydub import AudioSegment
    from pydub.silence import detect_silence

    print("[2/5] Detecting silence gaps (beat boundaries)...")
    audio = AudioSegment.from_wav(str(wav_path))

    # Try progressively looser settings until we get useful gaps
    for min_len, thresh in [(1500, -40), (800, -45), (600, -42)]:
        silences = detect_silence(audio, min_silence_len=min_len, silence_thresh=thresh)
        # Filter out end-of-file silence only
        meaningful = [s for s in silences if s[0] < len(audio) - 5000]
        if len(meaningful) >= 3:
            print(f"    Settings: min_len={min_len}ms  thresh={thresh}dBFS  → {len(silences)} gaps")
            break

    gaps = []
    for i, (start_ms, end_ms) in enumerate(silences):
        s, e = start_ms / 1000, end_ms / 1000
        gaps.append({
            "index": i + 1,
            "start": round(s, 2),
            "end": round(e, 2),
            "duration": round((end_ms - start_ms) / 1000, 2),
            "start_fmt": f"{int(s//60)}:{int(s%60):02d}",
            "end_fmt": f"{int(e//60)}:{int(e%60):02d}",
        })
        print(f"    Gap {i+1:2d}: {gaps[-1]['start_fmt']} → {gaps[-1]['end_fmt']}  ({gaps[-1]['duration']:.2f}s)")

    out = out_dir / "silence_gaps.json"
    out.write_text(json.dumps(gaps, indent=2))
    print(f"    Saved: {out.name}")
    return gaps


# ──────────────────────────────────────────────
# STEP 3: Transcribe
# ──────────────────────────────────────────────

def transcribe(wav_path: Path, out_dir: Path, language: str, model: str) -> list:
    import whisper as _whisper

    print(f"[3/5] Transcribing with Whisper ({model}, lang={language})...")
    print("    This may take 2-5 minutes for an 8-min audio...")

    model_obj = _whisper.load_model(model)
    result = model_obj.transcribe(str(wav_path), language=language, verbose=False)

    segments = [
        {
            "id": s["id"],
            "start": round(s["start"], 2),
            "end": round(s["end"], 2),
            "start_fmt": f"{int(s['start']//60)}:{int(s['start']%60):02d}",
            "text": s["text"].strip(),
        }
        for s in result["segments"]
    ]

    transcript = {
        "source": wav_path.parent.name,
        "language": language,
        "model": model,
        "duration_seconds": result.get("duration", 0),
        "segments": segments,
    }

    out = out_dir / "transcript.json"
    out.write_text(json.dumps(transcript, indent=2, ensure_ascii=False))
    print(f"    {len(segments)} segments saved → {out.name}")

    print("\n    --- FIRST 5 SEGMENTS ---")
    for s in segments[:5]:
        print(f"    [{s['start_fmt']}] {s['text']}")
    print("\n    --- LAST 5 SEGMENTS ---")
    for s in segments[-5:]:
        print(f"    [{s['start_fmt']}] {s['text']}")

    return segments


# ──────────────────────────────────────────────
# STEP 4: Build cue sheet
# ──────────────────────────────────────────────

def build_cue_sheet(gaps: list, segments: list, out_dir: Path, num_cues: int) -> list:
    """
    Divide the video into music cues using silence gap timestamps.
    Groups gaps into num_cues sections by selecting the largest/most-spaced gaps as dividers.
    """
    print(f"[4/5] Building {num_cues}-cue music plan...")

    total_duration = segments[-1]["end"] if segments else 486.0

    # Pick the best gap timestamps as cue boundaries
    # Sort by gap size descending, pick top (num_cues - 1) as dividers
    sorted_gaps = sorted(gaps, key=lambda g: g["duration"], reverse=True)
    dividers = sorted([g["start"] for g in sorted_gaps[:num_cues - 1]])

    # Build cue time ranges
    boundaries = [0.0] + dividers + [total_duration]
    boundaries = sorted(set(boundaries))

    def fmt(s):
        return f"{int(s//60)}:{int(s%60):02d}"

    def get_snippet(start, end):
        chunk = [seg["text"] for seg in segments if start <= seg["start"] < end]
        text = " ".join(chunk)
        return text[:120] + "..." if len(text) > 120 else text

    # Generic mood/prompt templates — adapt per project
    mood_templates = [
        ("tension + intrigue + mystery",
         "Tense cinematic opening. Low drone strings, sparse piano stabs, subtle percussion. 60 BPM. Dark and mysterious. No melody — just mood and pulse. No brass fanfares, no major-key brightness."),
        ("analytical + unsettled + curious",
         "Minimalist science-thriller underscore. Sparse electronic textures over plucked strings. Steady rhythmic pulse, 72 BPM. Slightly eerie. No vocals. No cinematic climax."),
        ("methodical + mounting tension",
         "Slow-burn documentary tension. Sustained string pad with heartbeat pulse, 65 BPM. Gradual harmonic movement. Ends on unresolved harmonic suspension."),
        ("revelation + ancient + awe",
         "Ancient mystery revealed. Deep percussion enters slowly under droning strings. Haunting woodwind melody. 55 BPM, rubato feel. Big but restrained — no triumphant orchestra."),
        ("wonder + ancient warmth + building",
         "Warm archaeological wonder. Layered acoustic textures, light melodic instrument, sustained strings. 70 BPM, forward-moving. Evokes deep time. Ends openly, not concluded."),
        ("suspense + twist + resolve",
         "Two-part climax. Part 1: thriller tension, syncopated strings, dissonant piano, 80 BPM. Part 2: resolution builds, momentum toward verdict. No full orchestral explosion."),
        ("warm + profound + resolution",
         "Gentle, profound resolution. Solo melodic instrument over soft string pad. 52 BPM, unhurried. Warm but not sentimental. Fades naturally over 8-10 seconds. No percussion. No drama."),
    ]

    cues = []
    for i, (start, end) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        idx = min(i, len(mood_templates) - 1)
        mood, prompt = mood_templates[idx]
        cues.append({
            "cue": i + 1,
            "start": fmt(start),
            "end": fmt(end),
            "duration_seconds": round(end - start),
            "filename": f"cue_{i+1:02d}_{mood.split(' + ')[0].replace(' ', '_')}.mp3",
            "transcript_snippet": get_snippet(start, end),
            "narrative_beat": f"Section {i+1} of {len(boundaries)-1} — narrative progresses from {fmt(start)} to {fmt(end)}.",
            "suggested_mood": mood,
            "lyria_prompt": prompt,
        })
        print(f"    Cue {i+1}: {fmt(start)} → {fmt(end)}  [{mood}]")

    out = out_dir / "cue_sheet.json"
    out.write_text(json.dumps(cues, indent=2, ensure_ascii=False))
    print(f"    Saved: {out.name}")
    return cues


# ──────────────────────────────────────────────
# STEP 5: Write Lyria prompts + CapCut guide
# ──────────────────────────────────────────────

def write_outputs(cues: list, video_name: str, out_dir: Path):
    print("[5/5] Writing lyria_prompts.txt + capcut_edit_guide.txt...")

    # Lyria prompts
    lines = [
        f"LYRIA MUSIC PROMPTS — {video_name}",
        "=" * 60,
        "Volume guideline: Mix all tracks at 12-18% under narration.",
        "",
    ]
    for c in cues:
        lines += [
            "─" * 60,
            f"PROMPT {c['cue']}  |  {c['start']} → {c['end']}  ({c['duration_seconds']}s)",
            f"File: {c['filename']}",
            f"Mood: {c['suggested_mood']}",
            f"Narrative: {c['narrative_beat']}",
            f"Snippet: {c['transcript_snippet']}",
            "",
            "LYRIA PROMPT:",
            c["lyria_prompt"],
            "",
        ]
    lines += [
        "=" * 60,
        "END OF PROMPTS",
        "",
        "Generation tips:",
        "- Generate each cue 5-10s longer than needed",
        "- Trim to exact duration with 1s fade in / 1.5s fade out",
        "- All cues should be loop-safe (no hard endings except last cue)",
    ]
    (out_dir / "lyria_prompts.txt").write_text("\n".join(lines), encoding="utf-8")

    # CapCut guide
    cap = [
        f"CAPCUT EDIT GUIDE — {video_name}",
        "=" * 60,
        "VOLUME RULE: Music at 12-18% while voice is active.",
        "            Fade in: 1s. Fade out: 1.5s at each boundary.",
        "",
        "─" * 60,
        f"TRACK 1: VOICE  ({video_name})",
        "─" * 60,
        f"  File:    {video_name}",
        "  Start:   0:00",
        "  Volume:  100%",
        "  Notes:   No cuts. Full video on Track 1.",
        "",
        "─" * 60,
        "TRACK 2: MUSIC CUES",
        "─" * 60,
    ]
    for c in cues:
        cap += [
            "",
            f"  CUE {c['cue']}",
            f"  File:       {c['filename']}",
            f"  Start:      {c['start']}",
            f"  End:        {c['end']}",
            f"  Duration:   {c['duration_seconds']}s",
            f"  Volume:     15%",
            f"  Fade in:    1s from {c['start']}",
            f"  Fade out:   1.5s before {c['end']}",
            f"  Mood:       {c['suggested_mood']}",
        ]
    cap += [
        "",
        "─" * 60,
        "EXPORT SETTINGS",
        "─" * 60,
        "  Resolution: 1080p",
        "  Codec:      H.264",
        "  Audio:      AAC 192kbps",
        f"  Filename:   {Path(video_name).stem}_SCORED.mp4",
    ]
    (out_dir / "capcut_edit_guide.txt").write_text("\n".join(cap), encoding="utf-8")

    print(f"    Saved: lyria_prompts.txt")
    print(f"    Saved: capcut_edit_guide.txt")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Score a video with music cues.")
    parser.add_argument("video", help="Path to .mp4 file")
    parser.add_argument("--language", default="ml", help="Whisper language code (default: ml)")
    parser.add_argument("--model", default="medium", help="Whisper model (default: medium)")
    parser.add_argument("--cues", type=int, default=7, help="Number of music cues (default: 7)")
    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    if not video_path.exists():
        print(f"Error: file not found: {video_path}")
        sys.exit(1)

    out_dir = video_path.parent
    print(f"\nScoring: {video_path.name}")
    print(f"Output:  {out_dir}\n")

    wav_path = extract_audio(video_path, out_dir)
    gaps = detect_gaps(wav_path, out_dir)
    segments = transcribe(wav_path, out_dir, args.language, args.model)
    cues = build_cue_sheet(gaps, segments, out_dir, args.cues)
    write_outputs(cues, video_path.name, out_dir)

    print("\n✓ All done. Files written to:", out_dir)
    print("  transcript.json")
    print("  silence_gaps.json")
    print("  cue_sheet.json")
    print("  lyria_prompts.txt")
    print("  capcut_edit_guide.txt")


if __name__ == "__main__":
    main()
