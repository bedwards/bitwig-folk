"""Show pipeline status for all Folk Sequence episodes."""

import json
import re
from datetime import datetime
from pathlib import Path

SOURCE_DIR = Path("/Volumes/Lacie/videos/folk-sequence")
OUTPUT_DIR = Path("output")
THUMBNAIL_DIR = OUTPUT_DIR / "thumbnails"
SCHEDULE_PATH = OUTPUT_DIR / "logs" / "schedule.json"


def show_status():
    """Print a table showing the pipeline status of every known episode."""
    episodes = set()
    source_mounted = SOURCE_DIR.exists()

    # Scan source .mov files
    source_episodes = set()
    if source_mounted:
        for p in SOURCE_DIR.glob("Folk Sequence *.mov"):
            m = re.search(r"Folk Sequence (\d{3})", p.stem)
            if m:
                ep = m.group(1)
                source_episodes.add(ep)
                episodes.add(ep)
    else:
        print("Source drive not mounted.")

    # Scan transcoded .mp4 files
    transcoded = set()
    for p in OUTPUT_DIR.glob("folk-sequence-*.mp4"):
        m = re.search(r"folk-sequence-(\d{3})", p.stem)
        if m:
            ep = m.group(1)
            transcoded.add(ep)
            episodes.add(ep)

    # Scan thumbnails
    thumbnails = set()
    for p in THUMBNAIL_DIR.glob("folk-sequence-*.jpg"):
        m = re.search(r"folk-sequence-(\d{3})", p.stem)
        if m:
            ep = m.group(1)
            thumbnails.add(ep)
            episodes.add(ep)

    # Load schedule
    schedule = {}
    if SCHEDULE_PATH.exists():
        try:
            entries = json.loads(SCHEDULE_PATH.read_text())
            for entry in entries:
                ep = entry["episode"]
                schedule[ep] = entry
                episodes.add(ep)
        except (json.JSONDecodeError, OSError):
            pass

    if not episodes:
        print("No episodes found.")
        return

    # Column headers and widths
    headers = ("Episode", "Source", "Transcoded", "Thumbnail", "Scheduled", "Uploaded")
    rows = []

    for ep in sorted(episodes):
        source = "yes" if ep in source_episodes else ("--" if source_mounted else "?")
        trans = "yes" if ep in transcoded else "no"
        thumb = "yes" if ep in thumbnails else "no"

        entry = schedule.get(ep)
        if entry:
            dt = datetime.fromisoformat(entry["publish_at"])
            sched = dt.strftime("%-m/%-d/%Y %-I:%M %p")
            vid = entry.get("video_id")
            uploaded = f"yes ({vid})" if vid else "--"
        else:
            sched = "--"
            uploaded = "--"

        rows.append((ep, source, trans, thumb, sched, uploaded))

    # Compute column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(val))

    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    for row in rows:
        print(fmt.format(*row))

    # Summary
    n_total = len(episodes)
    n_transcoded = len(transcoded)
    n_thumbnails = len(thumbnails)
    n_scheduled = sum(1 for e in schedule.values() if e.get("publish_at"))
    n_uploaded = sum(1 for e in schedule.values() if e.get("video_id"))

    print()
    print(
        f"Total: {n_total} episodes | {n_transcoded} transcoded | "
        f"{n_thumbnails} thumbnails | {n_scheduled} scheduled | {n_uploaded} uploaded"
    )
