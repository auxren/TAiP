#!/usr/bin/env python3
"""taip: chop and tag a raw live tape with ffmpeg + flac.

Subcommands (each prints what it did; nothing runs silently):

  probe   FILES...             formats, durations, BWF start stamps, how files chain
  plan    FILES... --setlist   find quiet stretches, pick cuts, write plan.json + plan.txt
  render  plan.json            cut, gain, FLAC-encode, tag, write info/md5/ffp
  verify  FOLDER               flac -t, tags, ffp, track-table checks
  offset  A B                  exact offset of recording B against recording A
  carry   plan.json            map a plan onto a second recorder of the same show

Needs: python3, numpy, ffmpeg/ffprobe, flac + metaflac. See docs/workflow.md.
"""
import argparse, hashlib, json, math, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

import numpy as np

ENV_RATE = 8000          # Hz the envelope/offset analysis decodes at
HOP = 0.1                # seconds per envelope frame
SEGUE = re.compile(r"\s*(?:->|>|»|→)\s*$")


# ───────────────────────── helpers ─────────────────────────

def die(msg):
    sys.exit(f"taip: {msg}")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def need(*tools):
    missing = [t for t in tools if not shutil.which(t)]
    if missing:
        die(f"missing {', '.join(missing)} — brew install ffmpeg flac (or your package manager)")


def parse_time(s):
    s = str(s).strip()
    parts = [float(p) for p in s.split(":")]
    t = 0.0
    for p in parts:
        t = t * 60 + p
    return t


def fmt_time(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def at_file(v):
    """'@path' reads a file; anything else is the literal text."""
    if v and v.startswith("@"):
        return Path(v[1:]).expanduser().read_text(encoding="utf-8", errors="replace").replace("\r", "\n").strip()
    return v or ""


def ffprobe(path):
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    if r.returncode:
        die(f"ffprobe failed on {path}: {r.stderr.strip()}")
    j = json.loads(r.stdout)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    if not a:
        die(f"{path} has no audio stream")
    dur = float(j["format"].get("duration") or a.get("duration") or 0)
    return {
        "path": str(Path(path).resolve()),
        "duration": dur,
        "rate": int(a["sample_rate"]),
        "channels": int(a["channels"]),
        "codec": a["codec_name"],
        "bits": int(a.get("bits_per_raw_sample") or a.get("bits_per_sample") or 0),
        "tags": {k.lower(): v for k, v in j["format"].get("tags", {}).items()},
    }


def bwf_start(path):
    """Seconds since local midnight from a BWF bext chunk (Sound Devices, Zoom F-series), or None."""
    try:
        with open(path, "rb") as f:
            head = f.read(1 << 16)
        i = head.find(b"bext")
        if i < 0:
            return None
        body = head[i + 8: i + 8 + 602]
        time_ref = int.from_bytes(body[338:346], "little")
        rate = int.from_bytes(head[24:28], "little") or 48000
        # originationTime at 330..338 is "HH:MM:SS"; timeReference is samples since midnight
        m = re.match(rb"(\d\d)[:-](\d\d)[:-](\d\d)", body[330:338])
        if time_ref and rate:
            return time_ref / rate
        if m:
            h, mi, s = (int(x) for x in m.groups())
            return h * 3600 + mi * 60 + s
    except OSError:
        pass
    return None


def decode_mono(path, channels, rate=ENV_RATE, start=None, dur=None):
    """float32 mono at `rate`, mixing the listed channel indices."""
    need("ffmpeg")
    cmd = ["ffmpeg", "-v", "error"]
    if start is not None:
        cmd += ["-ss", f"{start:.6f}"]
    if dur is not None:
        cmd += ["-t", f"{dur:.6f}"]
    cmd += ["-i", str(path), "-af", pan_filter(channels, mono=True), "-ar", str(rate), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode:
        die(f"ffmpeg decode failed on {path}: {r.stderr.decode(errors='replace').strip()}")
    return np.frombuffer(r.stdout, dtype="<f4")


def pan_filter(channels, mono=False):
    # Fold by hand with an explicit pan matrix. Never let a resampler "downmix" a
    # multichannel file for you: 6 discrete tracks can fold to silence without an error.
    if mono:
        w = 1.0 / len(channels)
        return "pan=mono|c0=" + "+".join(f"{w:.6f}*c{c}" for c in channels)
    if len(channels) == 1:
        return f"pan=mono|c0=c{channels[0]}"
    return "pan=stereo|c0=c%d|c1=c%d" % (channels[0], channels[1])


def concat_list(files):
    fd, name = tempfile.mkstemp(prefix="taip-concat-", suffix=".txt")   # unique per process: parallel runs must not share a list
    with os.fdopen(fd, "w") as f:
        for p in files:
            f.write("file '%s'\n" % str(p).replace("'", "'\\''"))
    return name


# ───────────────────────── setlist ─────────────────────────

def parse_setlist(text):
    """Loose setlist → [{'set': 1, 'title': ..., 'segue': bool}], plus set labels."""
    songs, labels, cur = [], {}, 1
    cur_label = None
    for raw in text.replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(set|encore|e)\s*(\d+)?\s*[:\-]?\s*$", line, re.I)
        if m:
            word = m.group(1).lower()
            if word == "set":
                n = int(m.group(2) or (max(labels) + 1 if labels else 1))
                cur, cur_label = n, f"Set {n}"
            else:
                cur = (max(labels) + 1) if labels else 1
                if cur_label and cur_label.lower().startswith("encore"):
                    cur = max(labels)
                cur_label = "Encore"
            labels[cur] = cur_label
            continue
        line = re.sub(r"^\s*(?:d\d+)?t?\d+[\.\)\-:]\s+", "", line)      # "1. ", "d1t03 ", "03) "
        seg = bool(SEGUE.search(line))
        title = SEGUE.sub("", line).strip()
        if not title:
            continue
        if cur not in labels:
            labels[cur] = cur_label or f"Set {cur}"
        songs.append({"set": cur, "title": title, "segue": seg})
    # renumber sets to 1..n in order of appearance
    order = sorted({s["set"] for s in songs}, key=lambda k: min(i for i, s in enumerate(songs) if s["set"] == k))
    remap = {old: i + 1 for i, old in enumerate(order)}
    for s in songs:
        s["set"] = remap[s["set"]]
    return songs, {remap[k]: v for k, v in labels.items() if k in remap}


# ───────────────────────── envelope and gaps ─────────────────────────

def envelope_db(x, rate=ENV_RATE):
    n = int(rate * HOP)
    frames = len(x) // n
    if frames == 0:
        return np.array([-120.0])
    p = (x[: frames * n].astype(np.float64) ** 2).reshape(frames, n).mean(axis=1)
    return 10 * np.log10(p + 1e-12)


def smooth_db(db, k=5):
    p = 10 ** (db / 10)
    sm = np.convolve(p, np.ones(k) / k, mode="same")
    return 10 * np.log10(sm + 1e-12)


def find_gaps(db, below, min_sec):
    """Quiet stretches (frames where smoothed level < median-below)."""
    sm = smooth_db(db)
    med = float(np.median(sm))
    thr = med - below
    quiet = sm < thr
    gaps, i, n = [], 0, len(sm)
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            gaps.append([i, j])
            i = j
        else:
            i += 1
    merged = []
    for g in gaps:                      # bridge <1 s blips of sound inside one stop
        if merged and (g[0] - merged[-1][1]) * HOP < 1.0:
            merged[-1][1] = g[1]
        else:
            merged.append(g)
    out = []
    for a, b in merged:
        dur = (b - a) * HOP
        if dur < min_sec:
            continue
        depth = med - float(np.percentile(sm[a:b], 10))
        out.append({"start": a * HOP, "end": b * HOP, "dur": dur, "depth": depth})
    return out, med


def music_span(db, med):
    sm = smooth_db(db, 20)
    on = np.where(sm > med - 10)[0]
    if len(on) == 0:
        return 0.0, len(db) * HOP
    return on[0] * HOP, (on[-1] + 1) * HOP


def cut_point(g):
    # Short stops: tapers cut late (≈70% through, so the applause tail stays with the song).
    # Long breaks: cut in the middle so each side keeps about a minute.
    frac = 0.5 if g["dur"] > 45 else 0.7
    return g["start"] + g["dur"] * frac


def choose_cuts(db, n_cuts, spacing=30.0):
    """Pick n_cuts quiet stretches; returns (cuts, gaps_used, notes)."""
    notes = []
    gaps = []
    for below in (8, 6, 4, 3):
        gaps, med = find_gaps(db, below, 1.5)
        if len(gaps) >= n_cuts:
            break
    lo, hi = music_span(db, med)
    cand = [g for g in gaps if g["start"] > lo + spacing and g["end"] < hi - spacing]
    if len(cand) < n_cuts:
        notes.append(f"only {len(cand)} quiet stretches for {n_cuts} cuts — add cuts by hand (insert) or lower --below")
    for g in cand:
        g["score"] = g["depth"] + 6 * math.log10(max(g["dur"], 1.0))
    picked = []
    for g in sorted(cand, key=lambda g: -g["score"]):
        if len(picked) == n_cuts:
            break
        if all(abs(cut_point(g) - cut_point(p)) >= spacing for p in picked):
            picked.append(g)
    picked.sort(key=lambda g: g["start"])
    return [round(cut_point(g), 2) for g in picked], picked, notes, (lo, hi)


# ───────────────────────── tape chain ─────────────────────────

def build_chain(files, join_gap=120.0):
    infos = [ffprobe(f) for f in files]
    t = 0.0
    chain = []
    for inf in infos:
        inf["offset"] = t
        t += inf["duration"]
        chain.append(inf)
    return chain, t


def describe_chain(chain):
    out = []
    prev_end = None
    for inf in chain:
        st = bwf_start(inf["path"])
        row = {"file": Path(inf["path"]).name, "dur": inf["duration"], "stamp": st}
        if st is not None and prev_end is not None:
            row["gap"] = st - prev_end
        if st is not None:
            prev_end = st + inf["duration"]
        out.append(row)
    return out


# ───────────────────────── commands ─────────────────────────

def cmd_probe(a):
    need("ffprobe")
    chain, total = build_chain(a.files)
    for inf, row in zip(chain, describe_chain(chain)):
        stamp = f"  start {fmt_time(row['stamp'])}" if row["stamp"] is not None else ""
        gap = ""
        if "gap" in row:
            g = row["gap"]
            gap = "  (contiguous)" if abs(g) < 1.0 else f"  gap {g:+.1f}s from previous"
        print(f"{row['file']}: {inf['channels']}ch {inf['rate']} Hz {inf['bits'] or '?'}-bit {inf['codec']}  {fmt_time(inf['duration'])}{stamp}{gap}")
    print(f"total {fmt_time(total)} across {len(chain)} file(s)")
    rates = {i["rate"] for i in chain}
    chans = {i["channels"] for i in chain}
    if len(rates) > 1 or len(chans) > 1:
        print("WARNING: files differ in rate/channels — they are not one tape; chop them separately.")
    if a.peaks:
        for inf in chain:
            r = run(["ffmpeg", "-nostats", "-i", inf["path"], "-af", "astats=measure_perchannel=Peak_level+RMS_level:measure_overall=none", "-f", "null", "-"])
            print(f"-- {Path(inf['path']).name}")
            for line in r.stderr.splitlines():
                if re.search(r"Channel: |Peak level dB|RMS level dB", line):
                    print("  ", line.split("] ", 1)[-1])


def parse_groups(specs, nch):
    groups = []
    for spec in specs or []:
        parts = spec.split("|", 2)
        if len(parts) < 2:
            die(f"--group wants 'name|0,1|source line', got {spec!r}")
        name, ch = parts[0], [int(c) for c in parts[1].split(",")]
        if max(ch) >= nch:
            die(f"group {name}: channel {max(ch)} but the tape has {nch}")
        groups.append({"name": name, "slug": re.sub(r"[^a-z0-9]+", "", name.lower()), "channels": ch,
                       "source": parts[2] if len(parts) > 2 else ""})
    if not groups:
        groups = [{"name": "", "slug": "", "channels": list(range(min(2, nch))), "source": ""}]
    return groups


def apply_cuts_file(tracks, text, total):
    """move <set> <cut> <time> | insert <set> <time> <title> | remove <set> <cut>   (sets/cuts 1-based as printed)"""
    def boundaries(set_no):
        idx = [i for i, t in enumerate(tracks) if t["set"] == set_no]
        return idx

    lines = [l.split("#", 1)[0].strip() for l in text.splitlines()]
    cmds = [l.split(None, 3) for l in lines if l]
    for c in sorted(cmds, key=lambda c: c[0] != "move"):             # all moves before inserts/removes
        op = c[0].lower()
        if op == "move":
            s, k, t = int(c[1]), int(c[2]), parse_time(c[3])
            idx = boundaries(s)
            i = idx[k - 1] + 1                                        # cut k is the end of the set's k-th track
            tracks[i - 1]["end"] = tracks[i]["start"] = t
        elif op == "insert":
            s, t, title = int(c[1]), parse_time(c[2]), c[3].strip()
            for i, tr in enumerate(tracks):
                if tr["start"] < t < tr["end"]:
                    new = {"set": s, "title": title, "segue": False, "start": t, "end": tr["end"]}
                    tr["end"] = t
                    tracks.insert(i + 1, new)
                    break
            else:
                die(f"insert at {c[2]} lands in no track")
        elif op == "remove":
            s, k = int(c[1]), int(c[2])
            i = boundaries(s)[k - 1]
            tracks[i]["end"] = tracks[i + 1]["end"]
            tracks[i]["segue"] = tracks[i + 1]["segue"]
            del tracks[i + 1]
        else:
            die(f"unknown cuts-file command {op!r}")
    return tracks


def cmd_plan(a):
    need("ffmpeg", "ffprobe")
    chain, total = build_chain(a.files)
    nch = chain[0]["channels"]
    groups = parse_groups(a.group, nch)
    primary = groups[0]
    print(f"decoding {len(chain)} file(s), {fmt_time(total)}, envelope from channels {primary['channels']} …")
    x = np.concatenate([decode_mono(i["path"], primary["channels"]) for i in chain])
    db = envelope_db(x)
    if a.dump_env:
        Path(a.dump_env).write_text("t,db\n" + "\n".join(f"{i*HOP:.1f},{v:.1f}" for i, v in enumerate(db)))

    songs, labels = ([], {})
    if a.setlist:
        songs, labels = parse_setlist(at_file(a.setlist) if a.setlist.startswith("@") else Path(a.setlist).read_text(errors="replace"))
        if not songs:
            die("setlist has no songs")
    n_cuts = (len(songs) - 1) if songs else (a.cut_count or 0)
    if n_cuts <= 0:
        die("give --setlist, or --cut-count N to list the N deepest quiet stretches")
    cuts, picked, notes, (lo, hi) = choose_cuts(db, n_cuts, a.spacing)
    start = max(0.0, lo - 3.0)
    end = min(total, hi + 5.0)
    edges = [start] + cuts + [end]
    tracks = []
    for i in range(len(edges) - 1):
        s = songs[i] if i < len(songs) else {"set": 1, "title": f"Track {i+1}", "segue": False}
        tracks.append({"set": s["set"], "title": s["title"], "segue": s["segue"], "start": edges[i], "end": edges[i + 1]})

    if a.cuts:
        tracks = apply_cuts_file(tracks, Path(a.cuts).read_text(), total)

    plan = {
        "files": [i["path"] for i in chain],
        "offsets": [i["offset"] for i in chain],
        "total": total, "rate": chain[0]["rate"], "bits": chain[0]["bits"], "codec": chain[0]["codec"],
        "groups": groups, "set_labels": labels, "tracks": tracks, "drop_titles": a.drop_title or [],
        "meta": {k: getattr(a, k) for k in ("artist", "date", "venue", "location", "prefix", "lineage",
                                            "recorded_by", "transferred_by", "target_db")},
        "gain": {g["name"]: None for g in groups},
    }
    for kv in a.gain or []:
        k, v = kv.split("=")
        plan["gain"][k] = float(v)
    plan["meta"]["personnel"] = at_file(a.personnel)
    plan["meta"]["notes"] = at_file(a.notes)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pre = a.prefix or "show"
    (out / f"{pre}.plan.json").write_text(json.dumps(plan, indent=1))
    table = render_table(plan, picked, notes)
    (out / f"{pre}.plan.txt").write_text(table)
    print(table)
    print(f"wrote {out}/{pre}.plan.json and .plan.txt — READ THE TRACK TABLE before rendering")
    if a.render:
        cmd_render(argparse.Namespace(plan=str(out / f"{pre}.plan.json"), out=a.out, no_normalize=a.no_normalize, jobs=1))


def render_table(plan, picked, notes):
    rows = ["  #  set  start        end          len      title"]
    flags = []
    for i, t in enumerate(plan["tracks"]):
        ln = t["end"] - t["start"]
        mark = ""
        if ln < 30:
            mark = "  <-- SHORT: a song behind?"
        elif ln > 20 * 60:
            mark = "  <-- LONG: missing cut(s)?"
        rows.append(f"{i+1:3d}  {t['set']:>3}  {fmt_time(t['start'])}  {fmt_time(t['end'])}  {fmt_time(ln)[2:]:>8}  {t['title']}{'  >' if t['segue'] else ''}{mark}")
        if mark:
            flags.append(i + 1)
    out = "\n".join(rows)
    if picked:
        out += "\n\nquiet stretches chosen (start, length, depth below the tape median):\n"
        out += "\n".join(f"  {fmt_time(g['start'])}  {g['dur']:6.1f}s  {g['depth']:4.1f} dB" for g in picked)
    for n in notes:
        out += f"\nNOTE: {n}"
    if flags:
        out += f"\nCHECK tracks {flags}: a very short or very long track means the cuts are off by a song."
    return out + "\n"


# ── render ──

def measure_peak_db(plan, group, lo, hi):
    lst = concat_list(plan["files"])
    try:
        r = run(["ffmpeg", "-nostats", "-f", "concat", "-safe", "0", "-ss", f"{lo:.3f}", "-t", f"{hi-lo:.3f}", "-i", lst,
                 "-af", pan_filter(group["channels"]) + ",astats=measure_perchannel=none:measure_overall=Peak_level", "-f", "null", "-"])
    finally:
        os.unlink(lst)
    m = re.findall(r"Peak level dB:\s*(-?[\d.]+|-?inf)", r.stderr)
    if not m:
        die("could not measure peak:\n" + r.stderr[-400:])
    return float(m[-1])


def info_text(plan, group, tracks, labels):
    m = plan["meta"]
    L = [m["artist"], f"{m['date']}", f"{m['venue']}, {m['location']}".strip(", "), ""]
    if m.get("personnel"):
        L += ["Lineup:", m["personnel"], ""]
    if group["source"]:
        L.append(f"Source: {group['source']}")
    if m.get("lineage"):
        L.append(f"Lineage: {m['lineage']}")
    if m.get("recorded_by"):
        L.append(f"Recorded by: {m['recorded_by']}")
    if m.get("transferred_by"):
        L.append(f"Transferred by: {m['transferred_by']}")
    L.append("")
    cur, n = None, 0
    for t in tracks:
        if t["set"] != cur:
            cur, n = t["set"], 0
            L += [(labels.get(str(cur)) or labels.get(cur) or f"Set {cur}") + ":"]
        n += 1
        L.append(f"  s{t['set']}t{n:02d}. {t['title']}{' >' if t['segue'] else ''}")
    if m.get("notes"):
        L += ["", m["notes"]]
    L += ["", "Chopped and tagged with TAiP (https://github.com/auxren/TAiP)."]
    return "\n".join(L) + "\n"


def cmd_render(a):
    need("ffmpeg", "flac", "metaflac")
    plan = json.loads(Path(a.plan).read_text())
    m = plan["meta"]
    for k in ("artist", "date", "prefix"):
        if not m.get(k):
            die(f"plan has no --{k}; re-run plan with it (the info file and every tag need it)")
    drop = set(plan.get("drop_titles", []))
    tracks = [t for t in plan["tracks"]]
    kept = [t for t in tracks if t["title"] not in drop]
    labels = plan.get("set_labels", {})
    album_base = f"{m['artist']} Live at {m['venue']}, {m['location']} on {m['date']}".replace(" at , ", " at ")
    total_tracks = len(kept)
    lst = concat_list(plan["files"])
    try:
        for g in plan["groups"]:
            folder = Path(a.out) / (f"{m['prefix']}-{g['slug']}" if g["slug"] else m["prefix"])
            folder.mkdir(parents=True, exist_ok=True)
            lo, hi = kept[0]["start"], kept[-1]["end"]
            gain = plan["gain"].get(g["name"])
            peak = None
            if gain is None and not a.no_normalize:
                peak = measure_peak_db(plan, g, lo, hi)
                target = float(m.get("target_db") if m.get("target_db") is not None else -0.5)
                gain = target - peak
                print(f"[{g['name'] or 'tape'}] peak {peak:+.2f} dBFS → gain {gain:+.2f} dB to land at {target} dBFS")
            gain = gain or 0.0
            bits24 = plan["bits"] in (0, 24, 32) and plan["codec"] != "pcm_s16le"
            n_in_set = {}
            for tn, t in enumerate(kept, 1):
                n_in_set[t["set"]] = n_in_set.get(t["set"], 0) + 1
                name = f"{m['prefix']}s{t['set']}t{n_in_set[t['set']]:02d}.flac"      # lowercase .flac always: some writers sniff the container from the extension
                tags = {"ARTIST": m["artist"], "ALBUMARTIST": m["artist"],            # ALBUMARTIST = ARTIST, or library apps scatter the album
                        "ALBUM": album_base + (f" - {g['name']}" if g["name"] else ""),
                        "TITLE": t["title"], "TRACKNUMBER": str(tn), "TRACKTOTAL": str(total_tracks),
                        "DISCNUMBER": str(t["set"]), "DATE": m["date"]}
                if m.get("venue"):
                    tags["VENUE"] = m["venue"]
                if g["source"]:
                    tags["COMMENT"] = g["source"]
                cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-ss", f"{t['start']:.4f}", "-t", f"{t['end']-t['start']:.4f}",
                       "-i", lst, "-af", pan_filter(g["channels"]) + (f",volume={gain:.4f}dB" if abs(gain) > 1e-6 else ""),
                       "-c:a", "flac"]
                cmd += ["-sample_fmt", "s32", "-bits_per_raw_sample", "24"] if bits24 else ["-sample_fmt", "s16"]
                for k, v in tags.items():
                    cmd += ["-metadata", f"{k}={v}"]
                cmd += [str(folder / name)]
                r = run(cmd)
                if r.returncode:
                    die(f"ffmpeg failed on {name}: {r.stderr.strip()[-400:]}")
                print(f"  {name}  {fmt_time(t['end']-t['start'])[2:]}  {t['title']}")
            lineage = m.get("lineage", "").replace("{gain}", f"{gain:+.2f} dB gain" if gain else "no gain change").replace(
                "{files}", f"{len(plan['files'])} recorder file(s) joined sample-exact")
            mm = dict(plan); mm["meta"] = dict(m, lineage=lineage)
            flacs = sorted(folder.glob("*.flac"))
            (folder / f"{m['prefix']}.txt").write_text(info_text(mm, g, kept, labels))
            ffp, md5 = [], []
            for f in flacs:
                sig = run(["metaflac", "--show-md5sum", str(f)]).stdout.strip()
                ffp.append(f"{f.name}:{sig}")
                md5.append(f"{hashlib.md5(f.read_bytes()).hexdigest()} *{f.name}")
            (folder / f"{m['prefix']}.ffp").write_text("\n".join(ffp) + "\n")
            (folder / f"{m['prefix']}.md5").write_text("\n".join(md5) + "\n")
            print(f"[{g['name'] or 'tape'}] wrote {len(flacs)} FLACs + info/ffp/md5 → {folder}")
    finally:
        os.unlink(lst)
    print("now run: taip verify <folder>   (decode the output with a foreign decoder before trusting it)")


def cmd_verify(a):
    need("flac", "metaflac", "ffprobe")
    folder = Path(a.folder)
    flacs = sorted(p for p in folder.iterdir() if p.suffix.lower() == ".flac")
    if not flacs:
        die(f"no FLACs in {folder}")
    bad = 0
    for f in flacs:
        if f.suffix != ".flac":
            print(f"BAD   {f.name}: extension must be lowercase .flac"); bad += 1
        t = run(["flac", "-t", "-s", str(f)])
        if t.returncode:
            print(f"BAD   {f.name}: flac -t failed: {t.stderr.strip()[:120]}"); bad += 1
            continue
        tags = {}
        for line in run(["metaflac", "--export-tags-to=-", str(f)]).stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1); tags[k.upper()] = v
        miss = [k for k in ("ARTIST", "ALBUMARTIST", "ALBUM", "TITLE", "TRACKNUMBER", "DISCNUMBER", "DATE") if not tags.get(k)]
        if miss:
            print(f"BAD   {f.name}: missing tags {miss}"); bad += 1
        elif tags["ALBUMARTIST"] != tags["ARTIST"]:
            print(f"WARN  {f.name}: ALBUMARTIST != ARTIST"); bad += 1
        else:
            dur = ffprobe(f)["duration"]
            print(f"ok    {f.name}  {fmt_time(dur)[2:]}  {tags['TITLE']}")
    ffps = list(folder.glob("*.ffp"))
    if not ffps:
        print("BAD   no .ffp"); bad += 1
    else:
        n = len([l for l in ffps[0].read_text().splitlines() if l.strip()])
        if n != len(flacs):
            print(f"BAD   ffp has {n} lines for {len(flacs)} FLACs"); bad += 1
    if not list(folder.glob("*.txt")):
        print("BAD   no info .txt"); bad += 1
    print("PASS" if not bad else f"{bad} problem(s)")
    sys.exit(1 if bad else 0)


# ── multi-recorder ──

def find_in(a, b, rate):
    """Slide `a` along `b`; return (index into b where a matches best, normalised score)."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    a = a - a.mean()
    b = b - b.mean()
    c = np.fft.irfft(np.fft.rfft(b, n) * np.conj(np.fft.rfft(a, n)), n)[: len(b) - len(a) + 1]
    e = np.concatenate([[0.0], np.cumsum(b.astype(np.float64) ** 2)])
    win = e[len(a):] - e[: len(b) - len(a) + 1]
    score = c / np.sqrt((a.astype(np.float64) ** 2).sum() * win + 1e-12)
    k = int(np.argmax(score))
    return k, float(score[k])


def cmd_offset(a):
    need("ffmpeg")
    ca = [int(c) for c in a.a_channels.split(",")]
    cb = [int(c) for c in a.b_channels.split(",")]
    xa = decode_mono(a.a, ca, start=a.a_start, dur=a.seconds)
    b0 = max(0.0, a.b_start - a.search)
    xb = decode_mono(a.b, cb, start=b0, dur=a.seconds + 2 * a.search)
    k, score = find_in(xa, xb, ENV_RATE)
    off = (b0 + k / ENV_RATE) - a.a_start
    print(f"B time = A time {off:+.4f} s   (correlation {score:.2f}; below 0.3 means no real match — use a louder, more distinctive window or widen --search)")
    if abs(k / ENV_RATE - (a.b_start - b0)) > a.search - 0.05:
        print("WARNING: the match sits on the search-window edge — the true peak is probably outside it. Widen --search.")


def cmd_carry(a):
    plan = json.loads(Path(a.plan).read_text())
    plan["files"] = [str(Path(f).resolve()) for f in a.files]
    chain, total = build_chain(a.files)
    plan["offsets"] = [i["offset"] for i in chain]
    plan["total"], plan["rate"], plan["bits"], plan["codec"] = total, chain[0]["rate"], chain[0]["bits"], chain[0]["codec"]
    for t in plan["tracks"]:
        t["start"] = max(0.0, t["start"] + a.offset)
        t["end"] = min(total, t["end"] + a.offset)
    plan["groups"] = parse_groups(a.group, chain[0]["channels"])
    plan["gain"] = {g["name"]: None for g in plan["groups"]}
    for kv in a.gain or []:
        k, v = kv.split("="); plan["gain"][k] = float(v)
    Path(a.out).write_text(json.dumps(plan, indent=1))
    print(f"wrote {a.out}: every cut shifted by {a.offset:+.3f}s. Per-take offsets drift across recorder hand-offs — "
          "for a multi-take recorder run carry once per take file and check each seam.")


def main():
    p = argparse.ArgumentParser(prog="taip", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("probe"); s.add_argument("files", nargs="+"); s.add_argument("--peaks", action="store_true"); s.set_defaults(fn=cmd_probe)

    s = sub.add_parser("plan")
    s.add_argument("files", nargs="+")
    s.add_argument("--setlist"); s.add_argument("--cut-count", type=int); s.add_argument("--cuts"); s.add_argument("--dump-env")
    s.add_argument("--artist", default=""); s.add_argument("--date", default=""); s.add_argument("--venue", default=""); s.add_argument("--location", default="")
    s.add_argument("--prefix", default=""); s.add_argument("--out", default="chopped")
    s.add_argument("--group", action="append", help="'name|0,1|source line' (repeat per mic pair)")
    s.add_argument("--lineage", default="{files} > {gain} > FLAC")
    s.add_argument("--recorded-by", default=""); s.add_argument("--transferred-by", default="")
    s.add_argument("--personnel", default=""); s.add_argument("--notes", default="")
    s.add_argument("--drop-title", action="append"); s.add_argument("--gain", action="append")
    s.add_argument("--target-db", type=float, default=-0.5); s.add_argument("--spacing", type=float, default=30.0)
    s.add_argument("--render", action="store_true"); s.add_argument("--no-normalize", action="store_true")
    s.set_defaults(fn=cmd_plan)

    s = sub.add_parser("render"); s.add_argument("plan"); s.add_argument("--out", default="chopped"); s.add_argument("--no-normalize", action="store_true"); s.set_defaults(fn=cmd_render)
    s = sub.add_parser("verify"); s.add_argument("folder"); s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("offset"); s.add_argument("a"); s.add_argument("a_channels"); s.add_argument("a_start", type=float)
    s.add_argument("b"); s.add_argument("b_channels"); s.add_argument("b_start", type=float)
    s.add_argument("--seconds", type=float, default=20); s.add_argument("--search", type=float, default=5); s.set_defaults(fn=cmd_offset)

    s = sub.add_parser("carry"); s.add_argument("plan"); s.add_argument("files", nargs="+"); s.add_argument("--offset", type=float, required=True)
    s.add_argument("--group", action="append"); s.add_argument("--gain", action="append"); s.add_argument("--out", required=True); s.set_defaults(fn=cmd_carry)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
