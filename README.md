# TAiP — Taper's AI Partner

Hand [Claude Code](https://claude.com/claude-code) a raw live recording and a setlist.
It chops the tape into tracks, tags the FLACs, writes the info file / md5 / ffp, checks its
own work with a foreign decoder, and (if you ask) uploads to archive.org.

This repo is the playbook and the tools. There is no app to install: Claude reads
[`CLAUDE.md`](CLAUDE.md) and the [`docs/`](docs), and drives
[`scripts/taip.py`](scripts/taip.py) (a thin layer over `ffmpeg` and `flac`).

## Quick start

1. Install [Claude Code](https://claude.com/claude-code) and the audio tools:
   ```sh
   brew install ffmpeg flac        # macOS; use apt/choco elsewhere
   ```
2. Clone this repo and start Claude **inside it**, so it reads `CLAUDE.md`, the skill and the docs:
   ```sh
   git clone https://github.com/auxren/TAiP && cd TAiP
   pip install -r requirements.txt   # numpy
   claude
   ```
3. Tell it what you have. Your tapes can live anywhere; give Claude the full path. It never
   touches the raw files and writes output to a `chopped/` folder next to them.
   If it can't read the folder, start with `claude --add-dir ~/Tapes`.

Claude asks before running commands. Approving `ffmpeg`, `ffprobe`, `flac`, `metaflac` and
`python3 scripts/taip.py` for the session is reasonable. Keep prompting on anything that
uploads or deletes.

## Prompts to start with

The shortest:

```
/chop-a-tape ~/Tapes/2026-10-08/MixPre-001.WAV setlist.txt
```

Everything up front, so it runs without questions:

```
Chop ~/Tapes/2026-10-08/*.WAV. Setlist is in ~/Tapes/2026-10-08/setlist.txt.
The Breaks, 2026-10-08, The Independent, San Francisco CA.
Source: Schoeps MK4 > Sound Devices MixPre-6 II (ch 1/2) > 32-bit float 96 kHz.
Recorded and transferred by Jane Taper. Research the lineup. Show me the track table
before you render.
```

From a photo of the stage sheet:

```
Here's the setlist: ~/Pictures/setlist.jpg. Transcribe it, tell me anything you can't read,
then chop ~/Tapes/show.wav with it.
```

Three mic pairs on one 6-channel recorder:

```
~/Tapes/MixPre-*.WAV is one show: ch 1/2 Schoeps MK22, ch 3/4 MK2s, ch 5/6 MK4.
Render each pair to its own folder with its own gain. Probe first and show me peaks per pair.
```

A second recorder (phone, second deck):

```
Primary is the MixPre chop you just made. phone.caf recorded the same show. Measure the offset
at two different songs, tell me if they disagree, carry the cuts across, and match loudness.
```

## When a cut is wrong

Read the track table with Claude and fix it in plain language:

```
Track 7 is 40 seconds and track 8 is 14 minutes. I think "Bertha" is missing a cut around 31:20.
Insert it and re-plan.
```

```
Move the Set 1 / Set 2 break to start at 1:12:40, drop the break itself, and re-render.
```

A track under ~30 s or over ~20 min usually means the cuts are off by a song. Segues (`>`) have
no gap to find, so give Claude a timestamp or ask it to listen either side. Then:

```
Verify the release. Tell me the true peak and loudness per folder, and extract 5 seconds at
three cut points so I can listen.
```

Claude won't upload unless you ask. More prompts, a troubleshooting table and the upload flow
are in [`docs/using-claude-code.md`](docs/using-claude-code.md).

## What's in here

| Path | What |
|---|---|
| `CLAUDE.md` | The standing orders Claude follows on every tape |
| `docs/using-claude-code.md` | Setup, permissions, prompt suggestions, how to fix cuts in plain language |
| `docs/workflow.md` | Step by step: probe → plan → review → render → verify |
| `docs/setlists.md` | Setlist format, taper Info.txt traps, personnel research |
| `docs/tagging.md` | Tag set, filenames, info file, md5/ffp conventions |
| `docs/multi-rig.md` | Several mic pairs, a second recorder, aligning them by samples |
| `docs/upload.md` | archive.org upload and the derive-stall gotcha |
| `docs/lessons.md` | Hard-won failure modes (silent downmixes, shared temp files, …) |
| `scripts/taip.py` | probe / plan / render / verify / offset / carry |
| `examples/` | Sample setlist, cuts file, personnel file |

## How the cutting works (honestly)

`taip plan` decodes an envelope, finds quiet stretches (applause, tuning, stops), and picks the
N−1 best for an N-song setlist. That is right most of the time and off by a song some of the
time, and segues (no gap) cannot be found from the audio at all. So the plan is always reviewed
as a track table, and fixes are one-line edits (`move` / `insert` / `remove`). Good-enough cuts
plus fast fixes beats chasing a perfect aligner.

## License

MIT. Taping and trading live music is only OK where the artist permits it. Check before you
upload.
