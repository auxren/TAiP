# Workflow

Everything below runs as `python3 scripts/taip.py …` (written `taip …` here; `alias taip='python3 scripts/taip.py'`). Keep raw files untouched; outputs go to
`chopped/` next to them.

## 0. Probe

```sh
taip probe MixPre-001.WAV MixPre-002.WAV --peaks
```

Prints each file's channels, rate, bit depth, duration and, for BWF files (Sound Devices,
Zoom), its start stamp and the gap from the previous file. Read it for:

- **One tape or several?** Files within ~2 s of contiguous are a 4 GB split of one tape. A gap of
  minutes is a recorder stop (often a deliberate set break). A soundcheck an hour earlier is not
  part of the release — leave it out of `plan`.
- **Channels.** A 6-channel recorder holds three stereo pairs. Name them with `--group`.
- **Peaks.** 32-bit float files often sit above 0 dBFS. `render` measures and pulls each pair
  down to −0.5 dBFS before writing 24-bit. A 24-bit file that already clips cannot be fixed;
  tell the user.

## 1. Setlist

Plain text. `Set 1:` / `Set 2:` / `Encore:` headers, one song per line, trailing `>` (or `->`,
`»`) for a segue. Numbering prefixes (`1.`, `d1t03`) are stripped. Lines starting `#` are ignored.
See `docs/setlists.md` for Info.txt traps.

## 2. Plan

```sh
taip plan MixPre-001.WAV MixPre-002.WAV --setlist setlist.txt \
  --artist "The Breaks" --date 2026-10-08 --venue "The Independent" --location "San Francisco, CA" \
  --prefix tb2026-10-08 --out chopped \
  --group "MK4|0,1|Schoeps MK4 > Sound Devices MixPre-6 II (ch 1/2) > 32-bit float 96 kHz" \
  --lineage "{files} > Taper's Bud > {gain} > FLAC 24/96" \
  --recorded-by "Jane Taper" --transferred-by "Jane Taper" \
  --personnel @personnel.txt
```

- `--prefix` is the file prefix: `<abbrev><date>` (`tb2026-10-08`). Files become
  `tb2026-10-08s1t01.flac`. Use the abbreviation the band already has on archive.org.
- `--group "name|ch,ch|source line"` once per mic pair. The first group's channels drive the cut
  detection. Output folders are `<prefix>-<name>/`. With no `--group`, channels 0,1 are used.
- `--lineage` may contain `{files}` and `{gain}`; they are filled in at render time.
- No setlist? `--cut-count 40` lists the 40 deepest quiet stretches so you can see the tape's
  structure.
- `--dump-env env.csv` writes the envelope (`t,db`) so you can see quiet stretches yourself.

Output: `<prefix>.plan.json` (the plan) and `<prefix>.plan.txt` (the table).

## 3. Review the table, fix with a cuts file

The table lists every track with start, end, length and set. Look for:

| You see | Probably |
|---|---|
| a track under 30 s | a cut landed on a mid-song dip, or a song is missing from the setlist |
| a track over 20 min | a cut missing (segue, or a gap too shallow to detect) |
| set breaks not at the longest stretches | the aligner is a song off before/after the break |
| fewer quiet stretches than songs | segues; add cuts by hand |

Anchors that are always available: recorder stops from `probe`; quiet stretches in the envelope
dump (count them against songs per set); and 3-second spot-listens:

```sh
ffmpeg -ss 1:48 -t 8 -i tape.wav -f wav - | ffplay -nodisp -autoexit -     # or just extract and open it
```

Write fixes to a cuts file (see `examples/cuts.txt`) — `move <set> <cut> <time>`,
`insert <set> <time> <title>`, `remove <set> <cut>` — and plan again with `--cuts cuts.txt`.
Sets and cuts are 1-based as printed; all moves run before removes and inserts.

**Long breaks.** A 40-minute set break should not become the tail of one song. Insert a throwaway
track titled `Set break` a minute after the closer and drop it at render:
`--drop-title "Set break"`.

## 4. Render

```sh
taip plan … --cuts cuts.txt --drop-title "Set break" --render
# or, from an existing plan:
taip render chopped/tb2026-10-08.plan.json --out chopped
```

Per pair: measure the peak over what will be written, set gain to `--target-db` (default −0.5),
cut, encode FLAC (24-bit unless the source was 16-bit), tag, and write `<prefix>.txt` (info),
`<prefix>.md5` and `<prefix>.ffp`. Override with `--gain MK4=+8.0`; skip with `--no-normalize`.

## 5. Verify

```sh
taip verify chopped/tb2026-10-08-mk4
```

Then do what the script can't:

```sh
metaflac --list --block-type=VORBIS_COMMENT chopped/…/tb2026-10-08s1t01.flac
ffmpeg -i chopped/…/tb2026-10-08s1t01.flac -af ebur128=peak=true -f null - 2>&1 | tail -12
```

- Tags say what the folder says (ALBUM, DISCNUMBER = set, ALBUMARTIST = ARTIST).
- True peak is where the `{gain}` line claims (≤ −0.5 dBFS).
- Track durations sum to the span you planned; no track is silent (check the RMS above).
- Extract 5 s at three cut points from the output and listen, or at least check that the level
  on each side of the seam looks like music, not a tune-up.

## 6. Hand back

Summarise: tracks and lengths, anything flagged, peaks, what you assumed. Offer to upload.
