# TAiP — standing orders

You are helping a taper turn a raw recording and a setlist into a finished, tagged,
verified FLAC release. The tool is `scripts/taip.py`; the method is `docs/workflow.md`.
Read that file before the first tape of a session. Run the tool as
`python3 scripts/taip.py <probe|plan|render|verify|offset|carry>`.

## The job, in order

1. **Intake.** Ask only for what you cannot find: the raw file(s), the setlist (a file, pasted
   text, or a photo of the stage sheet — read the photo yourself), artist, date, venue, city,
   and the taper's mic chain (the "Source" line). Everything else you work out.
2. **Probe** every file (`probe --peaks`). Decide what the tape is: one file or a chain, how many
   channels, which channels are which mic pair, whether a second recorder exists.
3. **Parse the setlist and count the songs** before touching the audio. If a taper's Info.txt is
   the source, strip prose lines, gear lines and credits first (`docs/setlists.md`).
4. **Research the touring lineup** (web search; Wikipedia credits, the band's site, the venue
   listing) and write it as `Real Name - instrument(s)`, one per line, to a personnel file. Do
   this BEFORE the first render: the info file is written at render time and a missed lineup
   costs a full re-render. If you cannot pin it down, ask the user instead of leaving it off.
5. **Plan**, then **read the track table**. A track under ~30 s or over ~20 min means the cuts
   are off by a song, however confident the plan looks. Fix with a cuts file and plan again.
6. **Render**, then **verify**. Never say "done" before `verify` exits 0 and you have looked at
   the output yourself (`docs/workflow.md` §Verify).
7. **Report** plainly: what was cut, what is uncertain (segues, long breaks, clipped peaks), what
   the user should listen to. Offer upload; never upload unasked.

## Rules that have each cost a real tape

- **Do not trust a plan because it looks tidy.** The failure mode is silent: ordinary
  confidence, wrong song. The track table and a spot-listen of 2–3 cut points are the check.
- **Never let a tool change a file's channel count behind your back.** Select channels with an
  explicit `pan` matrix (`taip.py` does). Auto-downmixing six discrete tracks can yield silence
  and report success. After any conversion, assert peak and RMS, not just format and duration.
- **Verify with a foreign decoder.** `flac -t` plus `metaflac --list`. A file that was written
  "correctly" and decodes nowhere else is not a release.
- **ALBUMARTIST = ARTIST** on every track, or library apps scatter the album.
- **Filenames end in lowercase `.flac`.** Some writers infer the container from the extension.
- **Never overwrite or delete the raw tape.** Output goes in a sibling folder. Re-running into a
  fresh output folder is cheaper than explaining a lost original.
- **Don't derive time offsets between recorders with `ffmpeg -ss` tricks.** Use `taip.py offset`
  (sample-correlated). A self-consistent wrong answer looks identical to a right one.
- **Gain is per mic pair.** One peak across all channels leaves a quieter pair far down. The
  tool does this; if you override with `--gain`, say so.
- **Don't write to a fixed temp path** in any script you add. Parallel runs will overwrite each
  other and mislabel audio. Use `mktemp`.
- **Good-enough cuts, fast fixes.** Fix what is badly wrong (a 20-minute track, a cut 90 s from
  the start). Don't chase a few seconds of precision; the taper will nudge cuts by ear.
- **Segues have no gap.** `>` songs run together; the audio can't locate them. Say so and ask
  the user for a timestamp, or find the song change by listening to a few seconds either side.
- **Stage-sheet setlists lie.** The band skips and reorders songs. If the track count doesn't fit
  the quiet stretches, say that before forcing it.

## Things to ask before doing

- Uploading to archive.org or anywhere else public.
- Deleting anything in the user's tape folder.
- Releasing a show if you suspect the artist doesn't allow taping.

Credentials (`IA_ACCESS_KEY`, `IA_SECRET_KEY`) come from the environment. Never write them to
a file in this repo, and never echo them.
