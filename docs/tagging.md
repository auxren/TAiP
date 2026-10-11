# Tagging and release conventions

## FLAC tags (written by `render`)

| Tag | Value |
|---|---|
| ARTIST | the artist |
| ALBUMARTIST | **same as ARTIST** (library apps group by it) |
| ALBUM | `Artist Live at Venue, City, ST on YYYY-MM-DD` (+ ` - <pair name>` for multi-pair) |
| TITLE | song title |
| TRACKNUMBER | continuous across the whole item (1…N), TRACKTOTAL = N |
| DISCNUMBER | the set number |
| DATE | `YYYY-MM-DD` |
| VENUE, COMMENT | venue; the source/mic chain |

Add more with `metaflac --set-tag=GENRE=… file.flac` if the user wants them. After dropping
throwaway tracks, TRACKTOTAL must be recounted (the renderer drops them before numbering, so it
is right; if you edit by hand, recount).

## File names

`<prefix>s<set>t<NN>.flac`, `NN` counting within the set: `tb2026-10-08s1t01.flac`. Always
lowercase `.flac`. Folder: `<prefix>` or `<prefix>-<pair>` for several pairs.

## Companion files

- `<prefix>.txt` — info file: artist, date, venue, lineup, **Source** (mic chain), **Lineage**
  (everything after the mic, down to the FLAC), recorded/transferred by, setlist with segues.
- `<prefix>.md5` — md5 of each FLAC file.
- `<prefix>.ffp` — `name.flac:<md5 of the decoded audio>`, one line per FLAC. Read it from
  STREAMINFO with `metaflac --show-md5sum`, so it survives re-tagging.

## Source and Lineage lines

Source: what the sound went through, mic to recorder, e.g.
`Schoeps MK4 (cardioid) > Sonosax M2D2 > Sound Devices MixPre-6 II > 32-bit float 96 kHz`.
Ask the taper; don't invent gear. Lineage: from the recorder file to the release, e.g.
`MixPre WAV (3 files joined sample-exact) > -4.7 dB to fit float peaks into 24-bit > FLAC 24/96`.

## Naming identifiers (archive.org)

`<abbrev><date>.<mic>`: `tb2026-10-08.mk4`. Use the band's existing abbreviation and collection
if they have them (check an older item).
