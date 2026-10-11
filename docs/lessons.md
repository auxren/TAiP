# Lessons (each one cost a real tape or a real afternoon)

- **A multichannel file can fold to silence and report success.** Some converters have no mix
  matrix for six discrete tracks, write zeros, and exit 0. The output has the right size, format
  and duration. Never let a converter change channel count; use an explicit `pan` matrix, and
  assert peak/RMS of anything you convert.
- **A "correct" FLAC that nothing else decodes.** A hand-written writer was spec-legal, passed
  its own tests, and was unplayable in some players. Decode what you write with a different
  decoder (`flac -t`, `afinfo`, ffprobe) and check the bytes that matter (bit depth in
  STREAMINFO), not just "it opened".
- **Container sniffing by extension.** A writer that infers the container from `.FLAC` (upper)
  can emit a non-FLAC. Write lowercase `.flac`, then rename.
- **Shared temp paths under parallel execution.** A fixed `/tmp/concat.txt` driven by `xargs -P 24`
  made workers decode each other's audio, and 20% of a corpus was mislabelled with normal-looking
  output. Use `mktemp`; prove a fix by comparing a serial run against two parallel runs
  byte-for-byte (two parallel runs agreeing proves nothing: a race agrees with itself).
- **Phantom songs.** Prose header lines parsed as songs shifted every real cut. Count songs first.
- **Self-consistent offsets.** `ffmpeg -ss` + resample gave an offset 422 ms wrong that was
  internally consistent. Measure with sample correlation; sanity-check a second way.
- **A result on the edge of its search window** is the signature of a true peak outside it.
- **One song behind.** An aligner was one song off in set 1 and two in set 2 with ordinary
  confidence scores. Only the track table (a 2-second track, a 30-minute track) showed it.
- **Gap-count matching is a coincidence machine.** "N−1 clear stops for N songs" tempts you to
  cut at every stop. On released shows it lost cuts in every variant: a soft verse stands in for
  a short real stop. Don't.
- **Set break anchoring is the exception.** A set break ≥10 min, at least twice the next longest
  stop and ≥20 dB deep is a reliable place to start set 2. The cut goes just before the music
  returns. Anything shorter or shallower is not.
- **Tapers cut late in a stop** (about 70% of the way through, so applause stays with the song);
  the midpoint of a short stop is within 3 s of the taper's cut only ~11% of the time. For
  breaks over ~45 s cut in the middle so each side keeps about a minute.
- **A recorder stop inside a long break** leaves digital silence, which defeats any
  "headroom from the bottom of the gap" measure. Cut long breaks out as their own track and drop it.
- **±3 s is the honest accuracy bar** for judging a cut against a taper's. Shorter tolerances are
  noise; longer ones flatter the tool.
- **A third of a folder of "tapes" aren't real tapes** (partial files, multiple versions, mixed
  sources). Look at the durations before assuming a folder is one show.
- **Tracks under the song-length floor are normal** at edges (a short opener, a short encore).
  A fixed 70 s minimum track length falsely declared 38% of legitimate shows impossible. Don't
  reject a plan for a short edge track.
- **Take hand-offs lose time.** A phone that stops and re-arms between takes dropped ~0.3 s each
  time, though its stamps claimed a small overlap. Trust samples over stamps.
- **Check the pair layout before trusting labels.** An analog copy of one pair arrived inverted
  and L/R swapped relative to two others.
- **Upload shows only some tracks?** It's the derive, not the upload (`docs/upload.md`).
