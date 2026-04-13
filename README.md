# VIBosing

AI-powered background music scoring for video. Drop an MP4 — VIBosing analyses speech, shot changes, and transcript, generates a composition plan, scores it with your music provider, and mixes the final video automatically.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
brew install ffmpeg

# Copy env template
cp .env.example .env

# Start the server
python3 app.py

# Open http://localhost:5000 (homepage)
# Open http://localhost:5000/composer.html (score composer)
```

## Workflow

1. **Drop a video** into the Score Composer (`composer.html`)
2. VIBosing auto-detects shot changes and starts Whisper transcription
3. Builds a voice-duck automation curve (music ducks under speech, rises in silence)
4. Connect an LLM to generate a cue sheet (narrative beats, moods, music direction)
5. Generate score via your chosen music provider
6. One-click mix: ffmpeg renders final video with music baked in
7. Download `scored.mp4`

## Music Providers

| Provider | Quality | Cost | Setup |
|---|---|---|---|
| ElevenLabs | Best | Paid credits | API key |
| Replicate (MusicGen) | Good | Pay-per-use | API key |
| HuggingFace | Free | Rate limited | Free account |

Set provider in the ⚙ settings panel in the composer.

## Project Structure

```
ancestor/
├── app.py              # Flask backend — all API endpoints
├── composer.html       # Cinematic score composer UI
├── index.html          # Homepage / product landing page
├── requirements.txt    # Python dependencies
├── .env                # API keys (not committed)
├── .env.example        # Template
│
├── uploads/            # All input videos (gitignored)
├── outputs/            # Per-video generated files (gitignored)
│   └── {video_stem}/
│       ├── shots.json        # Shot change timestamps
│       ├── cues.json         # Music cue sheet
│       ├── transcript.json   # Whisper transcript segments
│       ├── automation.json   # Volume keyframes [[time, vol], ...]
│       ├── score.mp3         # Generated background score
│       └── scored.mp4        # Final mixed video
└── archive/            # Old artifacts from v0.1–v0.3 (kept for reference)
```

## Tech Stack

- **Frontend**: Vanilla HTML/CSS/JS, Canvas API (multi-lane timeline)
- **Backend**: Flask, python-dotenv
- **Analysis**: Whisper (transcription), ffmpeg (shots + mixing), librosa (voice energy)
- **Music Generation**: ElevenLabs / Replicate MusicGen / HuggingFace (swappable)
- **Intelligence**: Claude API (cue generation from transcript + shots)

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/upload` | POST | Upload video → `uploads/` |
| `/api/analyze-full` | POST | Detect shots, load cues/transcript/automation |
| `/api/transcribe` | POST | Start async Whisper job |
| `/api/transcribe/status/:id` | GET | Poll transcription progress |
| `/api/build-automation` | POST | Build duck curve from transcript segments |
| `/api/generate-cues` | POST | Claude generates cue sheet |
| `/api/music/generate` | POST | Generate score (routes to active provider) |
| `/api/mix-video` | POST | ffmpeg mix: video + score → scored.mp4 |
| `/api/download/:stem/:file` | GET | Download output file |
| `/api/load/:stem/:file` | GET | Load JSON from outputs/{stem}/ |
| `/api/settings` | GET/POST | Read/write API keys and provider config |

## Version History

- **v0.1** — Intelligent background scoring concept, Flask backend, first pipeline
- **v0.2** — First scored video complete (The Missing Ancestor)
- **v0.3** — Light-theme composer UI, YouTube assets
- **v0.4** — Dynamic composer (any video), cinematic dark UI, multi-lane timeline, AI suggestions panel, multi-provider music generation, per-video isolated outputs
