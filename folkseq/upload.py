"""Upload transcoded video to YouTube with scheduled publish time."""

import json
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("output")
SCHEDULE_PATH = OUTPUT_DIR / "logs" / "schedule.json"
ESSAYS_PATH = OUTPUT_DIR / "logs" / "essays.json"
LOGS_DIR = OUTPUT_DIR / "logs"

# Global base tags applied to every Folk Sequence video.
# Per-episode extra tags are registered via `folkseq essay --tags`.
BASE_TAGS = [
    "bitwig",
    "bitwig studio",
    "bitwig 6",
    "folk",
    "folktronica",
    "folk music production",
    "ambient folk",
    "alt country",
    "americana",
    "electronic folk",
    "music production no talking",
    "bitwig session",
    "daw walkthrough",
    "no narration",
    "screen recording",
]


def _load_essay(episode):
    """Load the registered essay for an episode, hard-failing if missing."""
    if not ESSAYS_PATH.exists():
        print("ERROR: No essays.json found.")
        print(f"Register an essay first: folkseq essay {episode} --url URL --title \"...\" --topic \"...\" --comment \"...\"")
        raise SystemExit(1)
    essays = json.loads(ESSAYS_PATH.read_text())
    essay = essays.get(episode)
    if not essay:
        print(f"ERROR: No essay registered for episode {episode}.")
        print(f"Register one first: folkseq essay {episode} --url URL --title \"...\" --topic \"...\" --comment \"...\"")
        raise SystemExit(1)
    if not essay.get("topic"):
        print(f"ERROR: Essay for episode {episode} is missing 'topic' (used for the SEO title).")
        print(f"Re-register with --topic: folkseq essay {episode} --url ... --title ... --topic \"...\" --comment ...")
        raise SystemExit(1)
    return essay


def _build_title(episode, essay):
    """Build the SEO title: 'Folk Sequence NNN — [topic]'."""
    return f"Folk Sequence {episode} — {essay['topic']}"


def _build_description(episode, essay):
    """Build the keyword-rich description with the companion essay block."""
    return (
        f"Folk Sequence {episode} — {essay['topic']}. "
        f"A folktronica and folk music production session in Bitwig Studio 6, "
        f"recorded as a continuous take with no narration, no edits, and no cuts. "
        f"Part of a daily series.\n\n"
        f"---\n\n"
        f"Companion essay: {essay['title']}\n"
        f"{essay['url']}\n\n"
        f"{essay['comment']}\n\n"
        f"jalopy.music\n"
    )


def _build_tags(essay):
    """Combine global base tags with the essay's per-episode tags."""
    extra = essay.get("tags", []) or []
    return BASE_TAGS + extra


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


def recover(episode):
    """Find an orphaned upload by title and patch schedule.json."""
    from googleapiclient.errors import HttpError
    from folkseq.auth import build_youtube
    from folkseq.schedule import next_publish_time, get_last_scheduled

    essay = _load_essay(episode)
    title = _build_title(episode, essay)
    youtube = build_youtube()

    print(f"Searching YouTube for: '{title}'")
    resp = youtube.search().list(
        part="id,snippet",
        q=title,
        type="video",
        maxResults=5,
        mine=True,
    ).execute()

    for item in resp.get("items", []):
        if item["id"]["kind"] != "youtube#video":
            continue
        vid = item["id"]["videoId"]
        vid_title = item["snippet"]["title"]
        if vid_title == title:
            print(f"Found: {vid}")
            # Patch schedule.json
            entries = load_schedule()
            entry = find_episode_entry(entries, episode)
            publish_time_iso = entry["publish_at"] if entry else None
            if entry:
                entry["video_id"] = vid
            else:
                entries.append({"episode": episode, "publish_at": publish_time_iso, "video_id": vid})
            save_schedule(entries)
            (LOGS_DIR / f"video-id-{episode}.txt").write_text(vid)
            print(f"schedule.json patched: {episode} -> {vid}")
            return vid
    print("No matching upload found.")
    return None


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

    # Load essay (hard-fails if missing) and build SEO metadata
    essay = _load_essay(episode)
    title = _build_title(episode, essay)
    description = _build_description(episode, essay)
    tags = _build_tags(essay)

    print(f"Episode:      Folk Sequence {episode}")
    print(f"Title:        {title}")
    print(f"Video:        {video_path}")
    print(f"Publish at:   {publish_time_iso}")

    # Build authenticated client
    youtube = build_youtube()

    # Video metadata
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
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

    # CRITICAL: persist video_id immediately — upload takes >5 min, may timeout
    (LOGS_DIR / f"video-id-{episode}.txt").write_text(video_id)
    (LOGS_DIR / f"video-id-latest.txt").write_text(f"{episode}:{video_id}")

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
    from folkseq.essay import attach_video_link_to_essay
    attach_video_link_to_essay(episode, video_id)

    # Add to "Folk Sequence — Full series" playlist if registered
    _add_to_playlist(youtube, video_id, episode)

    print("Done.")


def _add_to_playlist(youtube, video_id, episode):
    """Add the freshly uploaded video to the channel playlist if one is registered."""
    from googleapiclient.errors import HttpError
    playlist_state = LOGS_DIR / "playlist.json"
    if not playlist_state.exists():
        return
    state = json.loads(playlist_state.read_text())
    playlist_id = state.get("playlist_id")
    if not playlist_id:
        return
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                },
            },
        ).execute()
        print(f"Added episode {episode} to playlist {state.get('title', playlist_id)}")
    except HttpError as e:
        print(f"WARNING: failed to add to playlist: {e}")
