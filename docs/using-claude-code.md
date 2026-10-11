# Using TAiP with Claude Code

## Setup (once)

1. Install Claude Code: https://claude.com/claude-code (needs a Claude subscription or API key).
2. Install the tools: `brew install ffmpeg flac` (macOS) and `pip install -r requirements.txt`.
3. Clone this repo and start Claude **inside it**, so it picks up `CLAUDE.md`, the skill and the docs:
   ```sh
   git clone https://github.com/auxren/TAiP && cd TAiP && claude
   ```
4. Your tapes can live anywhere. Give Claude the full path; it never modifies the raw files and
   writes output to a sibling `chopped/` folder. If Claude asks permission to read a folder,
   approve that folder (or start with `claude --add-dir ~/Tapes`).

## Permissions

Claude asks before running commands. For a chop it will run `ffmpeg`, `ffprobe`, `flac`,
`metaflac` and `python3 scripts/taip.py`. Approving those for the session ("don't ask again")
is reasonable. Keep prompting on anything that uploads, deletes, or touches files outside your
tape and output folders.

## The shortest prompt

```
/chop-a-tape ~/Tapes/2026-10-08/MixPre-001.WAV setlist.txt
```

Claude asks for whatever is missing (artist, date, venue, city, mic chain).

## Prompts that work

Give everything up front and it runs without questions:

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

From a taper's Info.txt (someone else's tape):

```
~/Tapes/Info.txt has the tracklist and gear. Parse it, tell me how many songs you count,
and tag the FLACs in ~/Tapes/flacs/ to match. Don't re-chop.
```

Hands-off, then a report:

```
Chop, render and verify ~/Tapes/show.wav with setlist.txt (artist/date/venue in the
filename show-2026-10-08-independent). Don't stop for review; tell me afterwards which
cuts you're least sure of.
```

Three mic pairs on one 6-channel recorder:

```
~/Tapes/MixPre-*.WAV is one show, three pairs: ch 1/2 Schoeps MK22, ch 3/4 MK2s, ch 5/6 MK4.
Render each pair to its own folder with its own gain. Probe first and show me peaks per pair.
```

A second recorder (phone, second deck):

```
Primary is the MixPre chop you just made. phone.caf recorded the same show. Measure the offset
at two different songs, tell me if they disagree, carry the cuts across, and match loudness.
```

## Fixing cuts

Read the table together. Plain language is enough; Claude turns it into a cuts file:

```
Track 7 is 40 seconds and track 8 is 14 minutes. I think "Bertha" is missing a cut around 31:20.
Insert it and re-plan.
```

```
Move the Set 1 / Set 2 break to start at 1:12:40, drop the break itself, and re-render.
```

```
Cut 4 of set 2 is a segue, so it's not in a gap. The song changes around 2:05:10. Listen
to 8 seconds either side and nudge it.
```

## Checking its work

```
Verify the release. Run the full checks, tell me the true peak and loudness per folder, and
extract 5 seconds at three cut points so I can listen.
```

If something sounds wrong, say where ("the seam at 41:07 clips the start of Dark Star"), not
what to change. Claude should measure before it edits.

## Upload

Claude won't upload unless you ask. When you do:

```
Show me the exact archive.org upload command and metadata for the MK4 folder. Don't run it yet.
```

Then reply "go" once you've read it. Keys come from your environment (`IA_ACCESS_KEY`,
`IA_SECRET_KEY`) or `ia configure`; never paste them into the chat.

## When it goes wrong

| Symptom | Say |
|---|---|
| Track table has a 20-minute track | "That track is missing a cut. Find the quiet stretches inside it." |
| Everything after a point is one song off | "From set 2 on, titles are one song early. Check the setlist count against the quiet stretches." |
| Fewer quiet stretches than songs | "Which songs are segues? Ask me for timestamps." |
| The setlist might be wrong | "The band may have skipped songs. Count quiet stretches per set and tell me what doesn't fit." |
| Cuts landed mid-applause | Fine; cuts sit late in short stops on purpose. Nudge by ear. |
| Output is silent | "Check peak and RMS of the output against the source." (see `lessons.md`) |
| Claude is guessing gear or lineup | "Ask me instead of guessing." |

## Tips

- Say what you can't give: "no setlist" means Claude lists the deepest quiet stretches and you
  name the songs together.
- Ask for the track table in the reply, not just a path to the file.
- For a long tape, ask Claude to run the render in the background and check the log.
- Found a failure mode? Tell Claude "add this to docs/lessons.md", then commit it.
