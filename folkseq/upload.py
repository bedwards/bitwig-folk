"""Upload transcoded video to YouTube with scheduled publish time."""

import json
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("output")
SCHEDULE_PATH = OUTPUT_DIR / "logs" / "schedule.json"
ESSAYS_PATH = OUTPUT_DIR / "logs" / "essays.json"
LOGS_DIR = OUTPUT_DIR / "logs"


def _build_description(episode):
    """Build the video description from the registered companion essay.

    Upload requires an essay to be registered first via `folkseq essay`.
    Raises SystemExit if no essay exists for the episode.
    """
    if not ESSAYS_PATH.exists():
        print(f"ERROR: No essays.json found.")
        print(f"Register an essay first: folkseq essay {episode} --url URL --title \"...\" --comment \"...\"")
        raise SystemExit(1)
    essays = json.loads(ESSAYS_PATH.read_text())
    essay = essays.get(episode)
    if not essay:
        print(f"ERROR: No essay registered for episode {episode}.")
        print(f"Register one first: folkseq essay {episode} --url URL --title \"...\" --comment \"...\"")
        raise SystemExit(1)
    return (
        "A screen recording session creating music in Bitwig Studio.\n\n"
        "---\n\n"
        f"Companion essay: {essay['title']}\n"
        f"{essay['url']}\n\n"
        f"{essay['comment']}\n\n"
        "jalopy.music\n"
    )


def load_schedule():
    """Load schedule.json, returning empty list if not found."""
    if not SCHEDULE_PATH.exists():
        return []
    return json.loads(SCHEDULE_PATH.read_text())


def save_schedule(entries):
    """Write schedule entries back to schedule.json."""
    SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_PATH.write_text(json.dumps(entries, indent=2) + "\n")


def find_episode_entry(entries, episode):
    """Find a schedule entry matching the given episode."""
    for entry in entries:
        if entry["episode"] == episode:
            return entry
    return None


def resolve_publish_time(episode, schedule):
    """Determine the ISO 8601 publish time for this episode.

    - schedule="next": look up episode in schedule.json
    - schedule=<ISO string>: use directly
    - schedule=None: look up in schedule.json; if missing, calculate next slot
    """
    if schedule == "next":
        entries = load_schedule()
        entry = find_episode_entry(entries, episode)
        if entry and entry.get("publish_at"):
            return entry["publish_at"]
        print(f"ERROR: Episode {episode} not found in schedule.json.")
        print("Run: uv run folkseq schedule")
        raise SystemExit(1)

    if schedule is not None:
        # Validate it parses as ISO 8601
        try:
            datetime.fromisoformat(schedule)
        except ValueError:
            print(f"ERROR: Invalid ISO 8601 datetime: {schedule}")
            raise SystemExit(1)
        return schedule

    # schedule is None: check schedule.json first, then calculate
    entries = load_schedule()
    entry = find_episode_entry(entries, episode)
    if entry and entry.get("publish_at"):
        return entry["publish_at"]

    # Calculate next available slot
    from folkseq.schedule import next_publish_time, get_last_scheduled

    last = get_last_scheduled()
    publish_time = next_publish_time(after=last)
    return publish_time.isoformat()


def upload(episode, schedule=None):
    """Upload a transcoded video to YouTube with metadata and thumbnail.

    Args:
        episode: Episode number as string (e.g., "001").
        schedule: Publish time — "next", an ISO 8601 string, or None.
    """
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    from folkseq.auth import build_youtube

    video_path = OUTPUT_DIR / f"folk-sequence-{episode}.mp4"
    thumb_path = OUTPUT_DIR / "thumbnails" / f"folk-sequence-{episode}.jpg"

    # Validate video file
    if not video_path.exists():
        print(f"ERROR: Video not found: {video_path}")
        print("Run: uv run folkseq transcode <source.mov>")
        raise SystemExit(1)

    # Check thumbnail (warn only)
    has_thumbnail = thumb_path.exists()
    if not has_thumbnail:
        print(f"WARNING: Thumbnail not found: {thumb_path}")
        print("Upload will proceed without a custom thumbnail.")

    # Resolve publish time
    publish_time_iso = resolve_publish_time(episode, schedule)
    print(f"Episode:      Folk Sequence {episode}")
    print(f"Video:        {video_path}")
    print(f"Publish at:   {publish_time_iso}")

    # Build description — include companion essay if registered
    description = _build_description(episode)

    # Build authenticated client
    youtube = build_youtube()

    # Video metadata
    body = {
        "snippet": {
            "title": f"Folk Sequence {episode}",
            "description": description,
            "tags": [
                "bitwig", "bitwig studio", "music production", "screen recording",
                "daw", "electronic music", "folk", "ambient", "generative",
            ],
            "categoryId": "10",  # Music
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_time_iso,
            "selfDeclaredMadeForKids": False,
        },
    }

    # Resumable upload
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=50 * 1024 * 1024,  # 50 MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    print("Uploading...")
    try:
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"  Upload {int(status.progress() * 100)}%")
    except HttpError as e:
        print(f"ERROR: YouTube upload failed: {e}")
        raise SystemExit(1)

    video_id = response["id"]
    print(f"Uploaded: https://youtu.be/{video_id}")

    # Set thumbnail
    if has_thumbnail:
        print("Setting thumbnail...")
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumb_path), mimetype="image/jpeg"),
            ).execute()
            print("Thumbnail set.")
        except HttpError as e:
            print(f"WARNING: Failed to set thumbnail: {e}")

    # Save full API response
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"upload-{episode}.json"
    log_path.write_text(json.dumps(response, indent=2) + "\n")
    print(f"Upload log saved to {log_path}")

    # Update schedule.json with video_id
    entries = load_schedule()
    entry = find_episode_entry(entries, episode)
    if entry:
        entry["video_id"] = video_id
    else:
        entries.append({
            "episode": episode,
            "publish_at": publish_time_iso,
            "video_id": video_id,
        })
    save_schedule(entries)
    print(f"Schedule updated with video_id: {video_id}")

    # Add YouTube link to companion essay gist (top and bottom)
    print("Updating companion essay gist with YouTube link...")
    from folkseq.essay import attach_video_link_to_gist
    attach_video_link_to_gist(episode, video_id)

    print("Done.")
