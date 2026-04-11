# VIBosing — Roadmap

## Done

- [x] **Audio extraction** — ffmpeg, metadata (duration, sample rate, channels)
- [x] **Whisper transcription** — 70 timestamped segments, medium model
- [x] **Silence gap detection** — 12 beat boundaries via pydub
- [x] **Cue sheet** — 7 cues with narrative beats, mood tags, Lyria prompts
- [x] **Music direction brief** — manual director's analysis, 54 volume keyframes
- [x] **Score Composer UI** — video player, waveform, automation curve, cue regions, playhead
- [x] **ElevenLabs panel** — 3 movement prompts, sting prompts, placement guide, credit tracker
- [x] **Flask backend** — app.py serving UI + API endpoints
- [x] **.env setup** — API key storage, .gitignore
- [x] **VIBosing homepage** — product landing page with workflow visualization

## In Progress — Current Video (The Missing Ancestor)

- [ ] **Shot change detection** — ffmpeg scene detection, overlay on timeline
- [ ] **Voice modulation analysis** — librosa energy/pitch/pace extraction per second
- [ ] **Script intelligence** — classify transcript segments (question/revelation/explanation/transition)
- [ ] **Auto-ducking curve** — generate volume automation from transcript timing
- [ ] **ElevenLabs compose-detailed** — one API call, full score, needs key permission fix
- [ ] **Cost preview** — show credit cost before generation
- [ ] **Audio mixing** — ffmpeg sidechain ducking to auto-mix music under voice

## Next — Make It Work for Any Video

- [ ] **Dynamic JSON loading** — drop video + cue_sheet.json, UI populates automatically
- [ ] **Claude API integration** — Opus analyses voice + shots + script → generates section plan
- [ ] **score_video.py upgrade** — replace hardcoded templates with Claude-driven analysis
- [ ] **One-click pipeline** — drop MP4, click Analyse, click Generate, get scored video
- [ ] **Adjustable automation** — drag keyframes to tweak volume curve in UI

## Future

- [ ] **NotebookLM automation** — when API is available, generate video from sources
- [ ] **Multi-language support** — Malayalam sync, same cue boundaries
- [ ] **CapCut project export** — export as CapCut-importable project file
- [ ] **Suno/Udio fallback** — alternative music generation backends
- [ ] **MusicGen self-hosted** — Meta's open-source model for offline generation
- [ ] **Batch processing** — score multiple videos in queue
- [ ] **Template system** — save scoring profiles (thriller, warm, educational) as reusable templates
