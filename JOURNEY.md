# VIBosing — The Journey
*From a NotebookLM video to a scored, YouTube-ready science film. Built entirely with Claude Code.*

---

## The Spark

It started with a video. I had been using Google NotebookLM to generate AI-narrated overviews of research topics — two voices, conversational, surprisingly watchable. The output was good. But it felt naked. No background music. No cinematic weight. Just two voices floating in silence.

The topic was one I cared about deeply: human evolution. The Missing Ancestor — a 7-million-year detective story written in our own DNA. The kind of subject that deserves a score.

So I asked: *can I build a tool that watches a video and composes the music for it?*

---

## What I Built

**VIBosing** (Vibe + Composing) is an intelligent background scoring tool for science explainer videos. Drop any video. It reads the voice, watches the cuts, understands the script — then generates a precisely timed background score.

The first episode scored: **The Missing Ancestor** — 8 minutes, 6 seconds, about human evolution and the fossil record.

---

## The Pipeline (What Actually Happens)

### Signal 1: The Transcript
Ran Whisper (medium model) on the extracted audio. Got 70 timestamped segments — every word, every pause, every beat of the narration tagged to the second.

### Signal 2: Voice Energy
Used librosa to analyse 487 frames of RMS energy, pitch, and speaking pace. Built a per-second profile of how dense the dialogue was — where the narrators were talking fast and urgent, where they slowed for weight, where silence opened up.

### Signal 3: Shot Detection
ffmpeg scene detection found 25 visual cuts across the 8-minute video. Every cut is a potential musical transition moment.

### Signal 4: Script Intelligence
Classified each segment by narrative function — cold open, evidence introduction, revelation, red herring, resolution. Mapped musical behaviour to meaning. A revelation moment needs a different sound than an analytical explanation.

### Signal 5: The Music Direction Brief
Combined all four signals into a professional film scoring brief. 7 cues. Each with:
- Exact time range
- Mood tag
- Narrative beat description
- Specific instrument palette and BPM
- "Do not" constraints (no triumphant brass, no pop rhythm)

### Signal 6: ElevenLabs Generation
Sent the brief to ElevenLabs `/v1/music` as a `composition_plan` — sections with local and global style descriptors. One API call per movement. Two calls total (5-minute limit per call). Joined with a 2-second crossfade. Total cost: $2.96.

---

## The Hardest Part: Mixing

Here's what nobody tells you about AI music generation: **the music never syncs to your script at the second level.** It follows its own internal timing. You describe a mood and get a mood — but not a beat that hits at 3:13 when the skull is revealed.

That's what the mixing pass is for.

### What we learned across 8 versions (v1 → v8):

**v1** — Flat mix at 15%. Verified the vibe was right. Sections were continuous. Moved forward.

**v2** — Full coverage. Music under the whole video. Now the problems were visible.

**v3** — Auto-duck curve. Voice energy analysis drove automatic volume ducking. Music drops when people talk. Felt mechanical.

**v4** — Raised the floor. 8% under voice was too low — music disappeared. Inaudible = boring. Raised minimum to 18%. Immediate improvement.

**v5** — Surgical keyframes. 88 volume segments manually crafted. DROPs only where dramatically earned. Soft dips (10%) instead of hard mutes everywhere. Music breathes instead of gasping.

**v6** — Punchline ducking. The emotional peak at 7:44–8:06 had 6 key lines. Duck DURING each line, swell BETWEEN them. Music peaks at 68% AFTER the last word. The emotional release lands.

**v7** — Removed the hard mute at 7:22. Replaced with a soft dip to 10%. It was killing the natural progression into the resolution.

**v8** — Same fix at 0:20. The opening cold-open silence was jarring. Soft dip. Done.

**Final result:** 88 keyframe segments. 3 strategic DROPs. One dramatic hard mute (3:13, the skull reveal — the only moment that earned it). One emotional peak at 68%. YouTube-ready.

---

## The Score Composer UI

Built a full web interface so this process is repeatable — not just a script, but a product.

**Stack:** Flask + vanilla HTML/CSS/JS

**What it does:**
- Drop any video → plays immediately in browser
- Web Audio API extracts and draws the waveform client-side
- Upload to server → shot detection + transcript + cue loading
- Timeline shows: waveform coloured by cue, volume automation curve, shot markers, playhead
- Sidebar: full transcript synced to playback, or cue detail with editable ElevenLabs prompts
- Copy any prompt → paste into API call

**Key design call:** The timeline is a spectrum, not discrete blocks. Cue colors bleed into each other. The music is continuous — the UI should reflect that.

---

## The Version History (What the Git Tells You)

| Version | What it was |
|---------|-------------|
| v0.1 | Python pipeline — analysis, cue sheet, Lyria prompts, CapCut guide |
| v0.2 | First scored video complete. ElevenLabs integration working. |
| v0.3 | Score Composer UI. Light theme, Linear-app aesthetic. Surgical mix v8. YouTube-ready final export. |
| v0.4 | **Dynamic composer.** Removed all hardcoded data. Now works for any video. |

---

## Numbers

| Metric | Value |
|--------|-------|
| Video duration | 8:06 |
| Transcript segments | 70 |
| Voice analysis frames | 487 |
| Shot changes detected | 25 |
| Volume keyframe segments | 88 |
| Mix iterations | 8 (v1 → v8) |
| ElevenLabs API calls | 2 (Part 1 + Part 2) |
| Total music generation cost | $2.96 |
| Final file size | 68 MB |
| Output format | H.264 720p, AAC 166kbps |

---

## What's Next

The composer is now a real product, not a single-video tool. The roadmap from here:

- **Claude API analysis** — drop a video, Opus analyses voice + shots + script → generates the cue sheet automatically
- **One-click pipeline** — drop MP4, click Analyse, click Generate, get scored video
- **Adjustable automation** — drag keyframes on the timeline to refine the volume curve
- **MusicGen local integration** — free tier for users without ElevenLabs credits
- **Malayalam version** — same cue boundaries, voice-over in Malayalam over the same score

---

## What This Experiment Proved

1. **AI music generation is viable for documentary scoring** — but only when treated as raw material, not finished product. The prompting gets you 70% there. The mixing pass gets you to professional.

2. **Voice energy is the right signal** — not shot changes, not silence gaps. Where the narrator breathes and how densely they speak is the primary driver of where music should live.

3. **Hard mutes almost never work** — use them once, where dramatically earned. Everywhere else, soft dips. The music should breathe with the content, not gasp.

4. **The iteration is the work** — v1 to v8 isn't failure. It's the process. Each version fixes one thing. Never change more than three things at once. Listen with your eyes closed.

5. **Tools built around a specific problem become general faster than you think** — we started with one 8-minute video about human ancestors. By v0.4, the tool works for any video.

---

*Built with Claude Code. First episode published on YouTube.*
*Repo: https://github.com/umshere/vibosing*
