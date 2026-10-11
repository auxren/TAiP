# Setlists, Info.txt files and the lineup

## Where a setlist comes from

In rough order of trust: the taper's own notes → a photo of the stage sheet → the band's
setlist.fm or fan-site page → the band's official site. Compare at least two when you can.
Photos of a stage sheet: read them directly, transcribe to the loose format, and point out
anything illegible rather than guessing.

## Count the songs first

When a chop "doesn't work", parse the setlist and count songs **before** blaming the audio. The
setlist is wrong more often than the alignment is.

A taper's `Info.txt` typically has: a few prose lines (band, date, venue), a "Recorded by" credit,
a numbered track list, and a gear-lineage line that may sit before **or after** the songs. Line
endings are often bare `\r` (old Mac editors), so split on both `\r` and `\n`.

- In a numbered list, an unnumbered line is **not** a song.
- Segue marks are `>`, `->`, `»`.
- Prose headers ("Live at …") once became phantom songs and dragged every real cut off its mark.
- The songs the **taper** lists are the truth for that tape; the band's website may list songs
  they didn't play or put them in a different order.

## Sets

`Set 1:` / `Set 2:` / `Encore:` become section numbers in order (`s1`, `s2`, `s3`). Leave a
soundcheck out of the main release, or it takes section 1 and shifts every set number.

## Personnel (do this every time)

Put the whole touring band in the info file, not just the headliner, in etree style:

```
Real Name (stage name, if any) - instrument(s)
```

Source them from something verifiable (album credits on Wikipedia, the tour page, the venue
listing) and pass them as `--personnel @personnel.txt`. If the sources disagree or the band
tours with rotating members, ask the user. A guess in a public info file is worse than a
question. Do it before the first render.

## Segues

About 13% of song changes in released shows are segues with no gap at all. The audio cannot find
them: not the quiet-stretch detector, not any amount of tuning. Treat them as a limit to
communicate. Ask for a timestamp, or listen around where the song is expected to change.
