---
name: chop-a-tape
description: Chop and tag a raw live-music recording from a setlist into verified, tagged FLACs with info/md5/ffp files. Use when the user gives a raw tape (WAV/CAF/FLAC) and a setlist, or asks to chop, split, tag or release a show.
---

Follow `CLAUDE.md` and `docs/workflow.md` in this repo. In short:

1. Collect: raw file(s), setlist, artist, date, venue, city, mic chain. Read photos of the stage
   sheet yourself.
2. `python3 scripts/taip.py probe <files> --peaks`; decide chain / pairs / second recorder.
3. Count songs in the setlist. Web-search the touring lineup; write `personnel.txt`.
4. `plan` with every flag you know. Read the track table. Fix with `--cuts` and re-plan until no
   track is under ~30 s or over ~20 min and the set breaks sit at the longest stretches.
5. Show the user the table and what you're unsure about (segues, long breaks) before rendering,
   unless they said to go all the way.
6. `render`, then `verify`, then the checks in docs/workflow.md §5. Spot-listen at three cuts.
7. Report. Offer upload; do not upload unasked.
