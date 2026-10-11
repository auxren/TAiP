# TAiP — Taper's AI Partner

Hand [Claude Code](https://claude.com/claude-code) a raw live recording and a setlist.
It chops the tape into tracks, tags the FLACs, writes the info file / md5 / ffp, checks its
own work with a foreign decoder, and (if you ask) uploads to archive.org.

This repo is the playbook and the tools. There is no app to install: Claude reads
[`CLAUDE.md`](CLAUDE.md) and the [`docs/`](docs), and drives
[`scripts/taip.py`](scripts/taip.py) (a thin layer over `ffmpeg` and `flac`).

## Use it

```sh
brew install ffmpeg flac        # or apt/choco equivalents
pip install -r requirements.txt # numpy
git clone https://github.com/auxren/TAiP && cd TAiP
claude                          # then:
```

> Chop `~/Tapes/2026-10-08/MixPre-001.WAV` — the setlist is in `setlist.txt`. Band is The Breaks,
> The Independent, San Francisco, 2026-10-08. Recorded with Schoeps MK4 > MixPre-6 II.

Claude will probe the files, research the touring lineup, plan the cuts, show you the track
table for review, render, verify, and tell you what it is unsure about. `/chop-a-tape` runs the
whole routine. More prompts, and what to say when a cut is wrong, are in
[`docs/using-claude-code.md`](docs/using-claude-code.md).

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
