# VIBosing — Roadmap

## Done ✓

### v0.1 — Foundation
- [x] Flask backend with audio extraction, Whisper transcription, shot detection
- [x] Silence gap detection via pydub
- [x] Voice modulation analysis (librosa energy/pitch/pace)
- [x] Auto-ducking curve from transcript + voice energy
- [x] Cue sheet generation (narrative beats, mood tags, composition prompts)
- [x] Music direction brief + scoring methodology documented

### v0.2 — First Scored Video
- [x] ElevenLabs music generation via compose-detailed API
- [x] Surgical volume automation (88 keyframes, 3 DROPs, punchline ducking)
- [x] Iterative mix refinement (v1→v8)
- [x] Final YouTube-ready export (The Missing Ancestor)

### v0.3 — UI Polish
- [x] Score Composer UI (video player, waveform, automation curve, cue regions, playhead)
- [x] VIBosing homepage (product landing page)
- [x] Light-theme composer with ElevenLabs panel

### v0.4 — Any Video, Any Provider
- [x] Dynamic composer — works for any video, not hardcoded to TMA
- [x] Cinematic dark UI — multi-lane timeline (ruler/frames/volume/waveform/voice)
- [x] AI suggestions panel — auto-fixable issues + director's call cards
- [x] Multi-provider music generation — ElevenLabs / Replicate MusicGen / HuggingFace free
- [x] Per-video isolated outputs — `outputs/{stem}/` so runs never interfere
- [x] Auto-pipeline — upload → shots → transcribe → duck curve → cues → score → mix
- [x] Mix button in composer — one-click ffmpeg render, download scored.mp4
- [x] STATE reset on new video load — no stale data from previous video
- [x] Fixed voice lane rendering — duck curve now correctly derived from automation keyframes
- [x] Provider-agnostic settings UI — ElevenLabs / Replicate / HuggingFace pills with setup hints
- [x] Export filename per video — `{stem}_score_data.json`
- [x] Workspace cleanup — archive/ for old artifacts, uploads/ for inputs, outputs/ for generated files

---

## Pending (Known Issues / Next Session)

- [ ] **Volume lane empty after transcription** — duck curve builds but VOLUME canvas shows blank until page reload (drawAll() timing)
- [ ] **Cue colours missing on waveform** — waveform renders but cue region colouring not applying on first load
- [ ] **HuggingFace free tier untested** — endpoint wired but API response format not verified
- [ ] **Replicate MusicGen per-section concat** — currently falls back to single long generation; proper per-section + ffmpeg concat not implemented
- [ ] **Frame thumbnail extraction** — frames-cv lane shows skeleton placeholders only; actual video frame capture not wired

---

## Up Next

- [ ] **Drag keyframes** — click-drag on automation lane to tweak volume curve live
- [ ] **Cue editor** — edit cue name, mood, time range directly in director's view panel
- [ ] **Score preview** — play score.mp3 alongside video in composer before mixing
- [ ] **Re-generate single cue** — replace one section's music without regenerating the full score
- [ ] **Mix level control** — slider to set overall music volume before final mix (currently fixed at auto-duck curve)
- [ ] **Batch queue** — drop multiple videos, process overnight
- [ ] **Export to CapCut** — write CapCut-importable draft XML with automation baked in

---

## Future

- [ ] **Multi-language transcription** — Malayalam (and other regional languages) support in Whisper
- [ ] **Visual temperature analysis** — extract colour palette per frame, map to harmonic warmth
- [ ] **Leitmotif tracking** — ensure recurring motif appears at designated story moments
- [ ] **Frequency-aware prompts** — avoid voice frequency range in music generation prompts
- [ ] **Template system** — save scoring profiles (thriller, warm, educational) as reusable presets
- [ ] **NotebookLM automation** — auto-generate script from sources when API is available

---

## Mixing Workflow (learned from v0.2 iterations)

The key insight: AI music generators don't sync to script beats. The mix pass is where the score becomes professional.

1. **Generate raw score** — ElevenLabs `composition_plan` sections, 2 calls × 5 min, joined with crossfade
2. **Flat mix test** — 15% constant volume, listen through for vibe + continuity
3. **Analyse energy vs script** — map librosa RMS against transcript, find mismatches
4. **Surgical automation** — 80–90 keyframes; DROPs only where dramatically earned (max 3); deep duck zones min 18%
5. **Punchline ducking** — duck DURING each punchline, swell BETWEEN; music peaks AFTER last word
6. **Iterate** — change max 2–3 things per version (v1→v8 for TMA)
