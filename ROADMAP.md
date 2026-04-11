# VIBosing — Roadmap

## Done

- [x] **Audio extraction** — ffmpeg, metadata (duration, sample rate, channels)
- [x] **Whisper transcription** — 70 timestamped segments, medium model
- [x] **Silence gap detection** — 12 beat boundaries via pydub
- [x] **Shot change detection** — 25 visual scene cuts via ffmpeg
- [x] **Voice modulation analysis** — librosa energy/pitch/pace, 487 frames
- [x] **Auto-ducking curve** — per-second volume automation from transcript + voice energy
- [x] **Cue sheet** — 7 cues with narrative beats, mood tags, prompts
- [x] **Music direction brief** — 6-signal analysis, 54 volume keyframes
- [x] **Scoring methodology** — professional film scoring approach documented
- [x] **Final score plan** — 12 sections with subtext, density, leitmotif, frequency awareness
- [x] **Score Composer UI** — video player, waveform, automation curve, cue regions, playhead
- [x] **ElevenLabs panel** — movement prompts, sting prompts, placement guide, credit tracker
- [x] **Flask backend** — app.py serving UI + API endpoints
- [x] **.env setup** — API key storage, .gitignore
- [x] **VIBosing homepage** — product landing page with workflow visualization
- [x] **ElevenLabs music generation** — compose API with composition_plan sections
- [x] **Score generation** — Part 1 (5.5 min) + Part 2 (2.7 min), joined with crossfade
- [x] **Surgical mixing** — 88 volume segments, 3 DROPs, punchline ducking, resolution swell
- [x] **Iterative refinement** — v1→v8 mix tweaking based on listening feedback
- [x] **Final export** — YouTube-ready H.264/AAC, quality verified

## The Mixing Workflow (learned from v1→v8 iterations)

The key insight: AI music generators don't sync to script beats. The mixing pass
is where the score becomes professional. Here's the workflow we developed:

### Step 1 — Generate raw score
- Use ElevenLabs `/v1/music` with `composition_plan` sections
- Split into 2 calls (5 min max per call), join with crossfade
- `positive_global_styles` + `negative_global_styles` for overall tone
- Per-section `positive_local_styles` + `negative_local_styles` for mood shifts
- Add "no vocals", "no singing", "instrumental only" to global negative styles

### Step 2 — Flat mix test
- Mix at constant 15% volume under the video
- Listen through: does the vibe match? Are sections continuous?
- This catches generation problems before spending time on automation

### Step 3 — Analyse score energy vs script
- Map generated score's actual energy (librosa RMS per 10s) against transcript
- Identify mismatches: music loud where it should be quiet and vice versa
- Don't try to make the music match — work WITH what it gives you

### Step 4 — Surgical volume automation
- Build ~80-90 volume keyframe segments in ffmpeg
- **DROPs**: only use hard mutes (0%) where dramatically earned (we kept only 3:13)
- **Soft dips**: for other emphasis moments, duck to 10% not 0%
- **Deep duck zones**: minimum 18% during dense dialogue (8% is too low — music disappears)
- **Boost weak zones**: if score energy drops, push volume UP to compensate
- **Edit transitions**: brief swell to 28-32% at shot change boundaries

### Step 5 — Punchline ducking
- For the emotional peak / closing lines: duck DURING each punchline, swell BETWEEN
- Music breathes with the words, not over them
- After the final spoken word, music peaks alone (68%) — the emotional release

### Step 6 — Listen and iterate
- Each version fixes one specific problem
- v1: flat mix → v2: full coverage → v3: auto-duck → v4: raised floor →
  v5: surgical → v6: punchline ducking → v7: soft dip at 7:22 → v8: soft dip at 0:20
- Never change more than 2-3 things per iteration

## Next — Make It Work for Any Video

- [ ] **Dynamic JSON loading** — drop video + cue_sheet.json, UI populates automatically
- [ ] **Claude API integration** — Opus analyses voice + shots + script → generates section plan
- [ ] **score_video.py upgrade** — replace hardcoded templates with Claude-driven analysis
- [ ] **One-click pipeline** — drop MP4, click Analyse, click Generate, get scored video
- [ ] **Adjustable automation** — drag keyframes to tweak volume curve in UI
- [ ] **Wire auto-duck + shot changes into composer UI** — show on timeline visually
- [ ] **MusicGen local integration** — free tier for users without API credits
- [ ] **Peppy/Guy Ritchie style** — alternative score generation with different prompts

## Future

- [ ] **NotebookLM automation** — when API is available, generate video from sources
- [ ] **Multi-language support** — Malayalam sync, same cue boundaries
- [ ] **CapCut project export** — export as CapCut-importable project file
- [ ] **Suno/Udio fallback** — alternative music generation backends
- [ ] **Batch processing** — score multiple videos in queue
- [ ] **Template system** — save scoring profiles (thriller, warm, educational) as reusable templates
- [ ] **Visual temperature analysis** — extract color palette per frame, map to harmonic warmth
- [ ] **Frequency-aware generation** — avoid voice frequency range in music prompts
- [ ] **Leitmotif tracking** — ensure recurring motif appears at designated moments
