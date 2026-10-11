# Several mic pairs and a second recorder

## Several pairs on one recorder

A 6-channel recorder holds three stereo pairs. Pass one `--group` per pair; each renders into its
own folder with its own Source line and its **own gain**. Confirm which channels are which:
mics on the same side of a bar correlate above 0.9 at 0 ms; opposite sides lag ~1 ms per 30 cm
of spacing; a negative best correlation is a polarity flip (an analog hop through another
device can invert and swap a pair). Use `taip offset` on two channels of the same file, or
`ffmpeg -af astats` per channel, rather than assuming the labels.

## A second recorder (phone, second deck)

The cuts are found once on the better-sounding or fuller recording, then carried across by a
**measured** offset.

1. Find the offset at a loud, distinctive moment (a song, not applause):
   ```sh
   taip offset primary.wav 0,1 3000  phone.caf 0,1 3000  --seconds 20 --search 30
   ```
   It prints `B time = A time +X s` and a correlation. Below 0.3 means no real match; pick
   another window. A match on the edge of the search window is wrong; widen `--search`.
2. Check it at a second moment far from the first. Clocks drift, and recorders that hand off
   between takes lose a fraction of a second at each seam.
3. Carry the plan:
   ```sh
   taip carry chopped/tb2026-10-08.plan.json phone.caf --offset 12.5 \
     --group "PH|0,1|iPhone, 24-bit 96 kHz" --out chopped/tb-phone.plan.json
   taip render chopped/tb-phone.plan.json --out chopped
   ```
4. For a recorder that takes several files, carry once per take file with its own offset, or
   measure each seam and check the cuts that straddle one.

Do not derive offsets through `ffmpeg -ss … -af aresample`. On a real show that route was 422 ms
from the frame-exact answer while looking perfectly self-consistent.

## Level-matching

Give the second recorder a plain gain (`--gain PH=-4.4`), no limiter, chosen so integrated
loudness matches the first (`ffmpeg -af ebur128` on each folder). A recorder whose input gain
was too hot clips at 0 dBFS and nothing can pull that back; say so in the report.

## Clocks

A recorder's clock can be minutes off. Don't align by timestamps alone: use them to find the
window, then correlate.
