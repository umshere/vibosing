# VIBosing

Intelligent background music scoring for video. Analyses voice, script, and scene cuts to compose a score that breathes with the content.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
brew install ffmpeg

# Add your API keys
cp .env.example .env
# Edit .env with your ElevenLabs key

# Start the server
python3 app.py

# Open http://localhost:5000
```

## How It Works

1. **Drop a video** into the Score Composer
2. VIBosing analyses voice modulation, shot changes, and transcript
3. Generates a volume automation curve and ElevenLabs composition plan
4. One click generates the background score via ElevenLabs API
5. Export a CapCut edit guide for final mixing

## Project Structure

```
vibosing/
├── index.html          # Homepage
├── composer.html       # Score Composer UI
├── app.py              # Flask backend
├── score_video.py      # CLI pipeline (analyse any .mp4)
├── .env                # API keys (not committed)
├── .env.example        # Template
├── requirements.txt    # Python dependencies
├── ROADMAP.md          # What's done, what's next
│
├── transcript.json     # Generated: Whisper transcript
├── silence_gaps.json   # Generated: beat boundaries
├── cue_sheet.json      # Generated: music cue plan
├── lyria_prompts.txt   # Generated: ready-to-paste prompts
├── capcut_edit_guide.txt
└── music_direction_brief.md
```

## Tech Stack

- **Frontend**: Vanilla HTML/CSS/JS, Web Audio API, Canvas
- **Backend**: Flask, python-dotenv
- **Analysis**: Whisper (transcription), ffmpeg (audio/shots), librosa (voice energy)
- **Music Generation**: ElevenLabs compose-detailed API
- **Intelligence**: Claude API (script understanding + section planning)
