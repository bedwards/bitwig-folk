"""Schedule videos for daily upload at 3:00 PM US Central Time."""

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")
PUBLISH_HOUR = 15  # 3:00 PM

OUTPUT_DIR = Path("output")
SCHEDULE_PATH = OUTPUT_DIR / "logs" / "schedule.json"


def next_publish_time(after=None):
    """Return the next available 3:00 PM Central publish slot.

    If after is None, uses tomorrow at 3:00 PM Central.
    If after is a datetime, returns the next day at 3:00 PM Central after that.
    """
    if after is None:
        tomorrow = date.today() + timedelta(days=1)
    else:
        tomorrow = after.date() + timedelta(days=1)
    return datetime(tomorrow.year, tomorrow.month, tomorrow.day, PUBLISH_HOUR, 0, 0, tzinfo=CENTRAL)


def get_last_scheduled():
    """Read schedule.json and return the latest publish_at datetime, or None."""
    if not SCHEDULE_PATH.exists():
        return None

    try:
        entries = json.loads(SCHEDULE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    if not entries:
        return None

    latest = None
    for entry in entries:
        dt = datetime.fromisoformat(entry["publish_at"])
        if latest is None or dt > latest:
            latest = dt

    return latest


def _load_schedule():
    """Load existing schedule entries from disk."""
    if not SCHEDULE_PATH.exists():
        return []

    try:
        return json.loads(SCHEDULE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def _save_schedule(entries):
    """Write schedule entries to disk, creating directories if needed."""
    SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_PATH.write_text(json.dumps(entries, indent=2) + "\n")


def _scan_transcoded():
    """Scan output/ for transcoded videos and return sorted episode numbers."""
    pattern = re.compile(r"^folk-sequence-(\d{3})\.mp4$")
    episodes = []
    if not OUTPUT_DIR.exists():
        return episodes

    for path in OUTPUT_DIR.iterdir():
        m = pattern.match(path.name)
        if m:
            episodes.append(m.group(1))

    return sorted(episodes)


def schedule_videos(start=None, days=7):
    """Schedule unscheduled transcoded videos for daily upload.

    Args:
        start: First episode to schedule (e.g., "001"). Default: next unscheduled.
        days: Maximum number of days/videos to schedule. Default: 7.
    """
    # Find transcoded videos
    transcoded = _scan_transcoded()
    if not transcoded:
        print("No transcoded videos found in output/.")
        raise SystemExit(1)

    # Load existing schedule
    schedule = _load_schedule()
    scheduled_episodes = {entry["episode"] for entry in schedule}

    # Find unscheduled episodes
    unscheduled = [ep for ep in transcoded if ep not in scheduled_episodes]

    # Filter by start episode if provided
    if start is not None:
        start_padded = start.zfill(3)
        unscheduled = [ep for ep in unscheduled if ep >= start_padded]

    if not unscheduled:
        print("No unscheduled episodes to schedule.")
        return

    # Get the last scheduled time as our starting point
    last_time = get_last_scheduled()
    publish_time = next_publish_time(after=last_time)

    # Schedule up to `days` episodes
    count = 0
    for episode in unscheduled[:days]:
        entry = {
            "episode": episode,
            "publish_at": publish_time.isoformat(),
            "video_id": None,
        }
        schedule.append(entry)
        print(f"Folk Sequence {episode} -> {publish_time.strftime('%Y-%m-%d %I:%M %p %Z')}")
        publish_time = next_publish_time(after=publish_time)
        count += 1

    _save_schedule(schedule)
    print(f"\nScheduled {count} video{'s' if count != 1 else ''}. "
          f"Total in schedule: {len(schedule)}.")
