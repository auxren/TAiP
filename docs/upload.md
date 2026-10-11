# Upload to archive.org

Only when the user asks, and only for artists who allow taping. Check the Live Music Archive /
the band's policy first.

## Credentials

`ia configure` (from `pip install internetarchive`) stores keys in `~/.config/ia.ini`, or export
`IA_ACCESS_KEY` / `IA_SECRET_KEY`. Never put keys in this repo.

## Show the command, then send

```sh
ia upload tb2026-10-08.mk4 chopped/tb2026-10-08-mk4/* \
  --metadata="mediatype:etree" --metadata="collection:etree" \
  --metadata="title:The Breaks Live at The Independent, San Francisco, CA on 2026-10-08 - Schoeps MK4" \
  --metadata="creator:The Breaks" --metadata="date:2026-10-08" \
  --metadata="venue:The Independent" --metadata="coverage:San Francisco, CA" \
  --metadata="source:<the Source line>" --metadata="lineage:<the Lineage line>" \
  --metadata="description:<the info file>"
```

Show the user the full command and metadata first; run it only on their go-ahead. Put a band collection in place of / in addition to `etree` if one
exists (`ia metadata` on a previous item of theirs shows it).

## "Only a few tracks show up"

Usually a stalled derive, not a failed upload. The details page lists only files it can stream,
so an item shows as many tracks as have MP3 derivatives. Check the public metadata, no login:

```sh
curl -s https://archive.org/metadata/<identifier> | python3 -c \
 'import json,sys,collections as c; print(c.Counter(f["format"] for f in json.load(sys.stdin)["files"]))'
```

Count `24bit Flac` / `Flac` against `VBR MP3`. If all FLACs are there, the upload worked; the
derive needs re-running, which is a write to a public item and the owner's call.
