# VIBosing — Scoring Intelligence Methodology

## How a professional film composer thinks, and how VIBosing replicates it.

---

## THE PROFESSIONAL PROCESS

When a composer like Hans Zimmer receives a rough cut, they don't start writing music. They do a **spotting session** — watching the entire film to decide WHERE music should exist, and more importantly, WHERE IT SHOULD NOT.

The output is a **cue sheet**: every music entry point, exit point, and the INTENT of each cue. Not "what instruments" — but "what should the audience FEEL here."

The most important principle in film scoring:

> **Music scores the subtext, not the text.**
> If someone says "I'm fine" but isn't fine, the music plays the hidden emotion.
> If the narrator says "they found a skull" — the music doesn't play "skull found."
> It plays "the weight of 7 million years of searching, ending in this moment."

This is what separates background music from a score.

---

## THE SIX SIGNALS

Professional composers analyse six layers before writing a note. VIBosing currently captures three. Here's the full picture.

### Signal 1 — Dialogue Rhythm ✅ WE HAVE THIS
**What it is:** When people talk, how fast, how loud, how emphatic.
**What we do:** librosa energy analysis per second. 487 data points.
**Professional term:** Ducking map.
**What we output:** Auto-duck curve (12% under speech, 30% in silence).

### Signal 2 — Edit Points / Shot Changes ✅ WE HAVE THIS
**What it is:** Where the visual cuts are. Each cut is a potential music transition.
**What we do:** ffmpeg scene detection. 25 cuts found.
**Professional term:** Edit Decision List (EDL).
**What we output:** shot_changes.json overlaid on timeline.

### Signal 3 — Script Intelligence ✅ WE HAVE THIS (partially)
**What it is:** Understanding WHAT is being said — is it a question, a revelation, an explanation?
**What we do:** Whisper transcript + manual classification of segments.
**Professional term:** Spotting notes.
**What we're missing:** We classify what's SAID but not the SUBTEXT. More below.

### Signal 4 — Subtext & Emotional Arc ❌ WE'RE MISSING THIS
**What it is:** The hidden emotional layer beneath the words.
**Professional term:** Playing the emotion vs playing the scene.

**Example from our video:**
- At 0:27, the host says *"Whoa, hold on, I'm from Cleveland."*
- The TEXT is a joke. The SUBTEXT is skepticism being set up to be demolished.
- A hack composer would play "funny." A real composer would play "the ground is about to shift under you" — because the audience needs to feel that this skepticism won't survive the next 8 minutes.

**Another example:**
- At 3:13, *"They found it. A skull."*
- The TEXT is a discovery. The SUBTEXT is vindication — decades of DNA prediction confirmed by physical evidence. The music should play VINDICATION, not just "discovery."

**How to add this to VIBosing:**
- Use Claude API to read each transcript segment and classify not just type (question/statement) but EMOTIONAL FUNCTION:
  - Setup (establishing an idea that will be challenged)
  - Challenge (skepticism, doubt, pushback)
  - Evidence (building the case)
  - Revelation (the payoff)
  - Vindication (proof of something predicted)
  - Reflection (letting truth settle)
  - Resolution (the final emotional landing)

### Signal 5 — Music Density & Breathing Room ❌ WE'RE MISSING THIS
**What it is:** How much musical COMPLEXITY to use at each point — not just volume but texture.

**Professional terms:**
- **Bed**: Sustained, low-density underscore beneath narration. Maintains emotional tone without competing with voice. ONE or TWO instruments. No rhythmic complexity.
- **Sting**: Short punctuating phrase at transitions or key reveals. 1-5 seconds.
- **Full score**: All instruments, melodic movement, harmonic complexity. Used SPARINGLY — maybe 10-15% of total runtime.

**The "Rule of Three":**
Professional composers vary density across three levels to prevent audience fatigue:
1. Bed (sparse, textural — 60% of runtime)
2. Transitional (moderate, some melody — 25% of runtime)
3. Full (all instruments, emotional peak — 15% of runtime)

If the music is always at the same density, the audience stops hearing it. Variation is what keeps it alive.

**Our video mapped to density levels:**

| Section | Time | Density | Why |
|---------|------|---------|-----|
| Cold open | 0:00–0:05 | Full | Hook before voice |
| Intro | 0:05–0:49 | Bed | Two hosts talking, setup |
| DNA evidence | 0:50–1:51 | Bed (minimal) | Dense technical info |
| Clock hunting | 1:52–2:50 | Transitional | Building toward reveal |
| Pre-reveal | 2:48–2:51 | Full (brief) | Swell into skull |
| SKULL | 3:13 | Silence→Sting | The DROP + hit |
| Post-skull | 3:18–4:03 | Transitional | Sacred/warm texture |
| Lucy/Habilis | 4:04–5:35 | Bed (minimal) | Longest info passage |
| Red herring | 5:36–6:53 | Transitional | Twist/tension |
| Verdict | 6:53–7:32 | Transitional→Full | Building |
| Resolution | 7:33–8:06 | FULL | Peak. Everything. |

### Signal 6 — Silence as Music ❌ WE'RE PARTIALLY DOING THIS
**What it is:** Deliberate absence of music as an emotional tool.
**Professional insight:** *"The absence of music is as much a part of the score as the music itself."* — Trent Reznor

We have 3 DROPs (0:20, 3:13, 7:22). But we haven't considered **processing pauses** — moments where the audience needs to sit with what they just heard, with NOTHING. No music, no sting, just the voice and its echo.

**Candidates for processing pauses in our video:**
- After *"Every person is African"* (0:22–0:24) — 2 seconds of nothing
- After *"the genetic scar where they merged"* (1:38–1:40) — let the image settle
- After *"A skull"* (3:15–3:17) — already a DROP, extend the silence
- After *"Case closed"* (7:24–7:26) — 2 seconds of nothing before resolution

---

## WHAT WE SHOULD ALSO CONSIDER (but aren't yet)

### Visual Temperature
Shot changes tell us WHEN the visual shifts. But not WHAT it shifts TO.
- Warm color grading (oranges, browns) → warm harmonic palette
- Cool color grading (blues, greys) → minor keys, sparse texture
- **How to add:** Extract dominant color per frame, map to musical warmth

### Frequency Space
Our video already has audio (two voices). The background music must avoid the frequency range where speech lives (300Hz–3kHz). This means:
- Use LOW instruments (sub-bass drones, low cello) and HIGH instruments (high flute, chimes) 
- Avoid mid-range melodic instruments that compete with voice
- **How to add:** Analyse spectral content of the voice track, generate music in complementary frequency bands

### Pacing Rhythm
How FAST are the cuts happening? Rapid cuts (3+ per 10 seconds) = high energy. Long holds (10+ seconds on one shot) = contemplative.
- **Our data:** 25 shots in 486 seconds = average 19.4s per shot
- But it's NOT uniform — some sections have rapid cuts, others hold
- **How to add:** Calculate cut density per 30-second window, map to music energy

### Leitmotif (Recurring Theme)
Professional scores have a CORE MUSICAL IDEA that recurs and evolves:
- A simple 3-4 note melody that appears first in the cold open
- Returns transformed at the skull discovery
- Returns FULLY RESOLVED at the "one human family" ending
- This creates subconscious emotional continuity

Current AI music generation can't easily do this. But we can approximate it by:
- Using the same key signature across all sections
- Requesting the same instrument (e.g., kalimba) to recur in sections 1, 4, and 7
- Describing the motif in every section prompt

---

## THE VIBOSING INTELLIGENCE STACK (what we build)

```
Layer 1: PHYSICAL SIGNALS (automated)
├── Voice energy per second (librosa)
├── Shot changes + cut density (ffmpeg)
├── Speech vs silence mapping (transcript)
└── Audio frequency analysis (librosa spectral)

Layer 2: NARRATIVE SIGNALS (Claude API)
├── Segment classification (question/revelation/explanation)
├── Emotional function (setup/challenge/evidence/vindication/reflection)
├── Subtext analysis (what the audience should FEEL vs what's SAID)
└── Pacing arc (where is the story accelerating vs breathing)

Layer 3: SCORING DECISIONS (Claude API)
├── Music density map (bed/transitional/full/silence)
├── Instrument selection per section (frequency-aware)
├── Hit points and stings (where music reacts)
├── Processing pauses (where to use deliberate silence)
├── Leitmotif placement (where core theme recurs)
└── Volume automation (auto-duck from transcript)

Layer 4: GENERATION (ElevenLabs / Suno / MusicGen)
├── compose-detailed sections from Layer 3 output
├── One coherent piece, all sections aware of each other
└── Post-processing: sidechain duck, fade automation
```

---

## THE KEY INSIGHT

Every tool in the market (Filmstro, AIVA, Mubert, Amper) does Layer 4 only — they generate music from a text prompt. None of them do Layers 1-3.

VIBosing's value is not in generating music. It's in the INTELLIGENCE that decides what music to generate, where, and why. The generation itself is a commodity — use whichever API is cheapest. The scoring intelligence is the product.

---

## PROFESSIONAL TERMS GLOSSARY

| Term | Meaning |
|------|---------|
| **Spotting session** | Watching the full video to decide where music goes |
| **Cue sheet** | Document listing every music entry/exit with intent |
| **Bed** | Low-density sustained underscore beneath narration |
| **Sting** | Short musical punctuation (1-5s) at key moments |
| **Ducking** | Reducing music volume when dialogue is present |
| **Mickey-mousing** | Over-literally matching music to on-screen action (avoid this) |
| **Diegetic** | Music that exists in the story world (a radio, a band playing) |
| **Non-diegetic** | Music only the audience hears (the score) |
| **Leitmotif** | Recurring musical theme tied to a character or idea |
| **Playing the subtext** | Scoring the hidden emotion, not the literal content |
| **Music density** | How much harmonic/rhythmic complexity is present |
| **Processing pause** | Deliberate silence for audience to absorb what happened |
| **Frequency masking** | When music and voice compete for the same frequency range |
