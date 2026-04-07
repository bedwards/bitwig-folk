"""Attach companion essays to Folk Sequence videos.

Each episode has a companion essay published as a public GitHub gist.
This module updates video descriptions and posts owner comments linking
to the essay. Comments cannot be posted on private/scheduled videos —
those are queued and posted automatically once the video goes public.
"""

import json
from pathlib import Path

OUTPUT_DIR = Path("output")
ESSAYS_PATH = OUTPUT_DIR / "logs" / "essays.json"
SCHEDULE_PATH = OUTPUT_DIR / "logs" / "schedule.json"


def _load_essays():
    if not ESSAYS_PATH.exists():
        return {}
    return json.loads(ESSAYS_PATH.read_text())


def _save_essays(essays):
    ESSAYS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ESSAYS_PATH.write_text(json.dumps(essays, indent=2) + "\n")


def _video_id_for_episode(episode):
    if not SCHEDULE_PATH.exists():
        return None
    schedule = json.loads(SCHEDULE_PATH.read_text())
    for entry in schedule:
        if entry["episode"] == episode:
            return entry.get("video_id")
    return None


def _make_description(title, url, comment):
    """Standard description footer with essay link."""
    return (
        "A screen recording session creating music in Bitwig Studio.\n\n"
        "---\n\n"
        f"Companion essay: {title}\n"
        f"{url}\n\n"
        f"{comment}\n\n"
        "jalopy.music\n"
    )


def add_essay(episode, gist_url, title, comment):
    """Register an essay for an episode and apply it to YouTube.

    Idempotent. Safe to re-run.
    """
    from folkseq.auth import build_youtube
    from googleapiclient.errors import HttpError

    essays = _load_essays()
    essays[episode] = {
        "title": title,
        "url": gist_url,
        "comment": comment,
        "comment_posted": essays.get(episode, {}).get("comment_posted", False),
    }
    _save_essays(essays)

    video_id = _video_id_for_episode(episode)
    if not video_id:
        print(f"Episode {episode} not yet uploaded — essay registered for later.")
        return

    youtube = build_youtube()

    # Update description (always safe — works on private and public videos)
    r = youtube.videos().list(part="snippet", id=video_id).execute()
    if not r.get("items"):
        print(f"Video {video_id} not found.")
        return
    snippet = r["items"][0]["snippet"]

    youtube.videos().update(
        part="snippet",
        body={
            "id": video_id,
            "snippet": {
                "title": snippet["title"],
                "description": _make_description(title, gist_url, comment),
                "tags": snippet.get("tags", []),
                "categoryId": snippet.get("categoryId", "10"),
            },
        },
    ).execute()
    print(f"Episode {episode}: description updated")

    # Try to post comment — fails on private videos
    if essays[episode]["comment_posted"]:
        print(f"Episode {episode}: comment already posted")
        return

    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": f"{comment}\n\n{gist_url}",
                        },
                    },
                },
            },
        ).execute()
        essays[episode]["comment_posted"] = True
        _save_essays(essays)
        print(f"Episode {episode}: comment posted")
    except HttpError as e:
        if "forbidden" in str(e).lower() or e.resp.status == 403:
            print(f"Episode {episode}: comment queued (video still private — will post after publish)")
        else:
            print(f"Episode {episode}: comment FAILED — {e}")


def post_pending_comments():
    """Retry posting comments for any essays where the video is now public.

    Run this periodically (e.g. after each daily 3 PM publish) or manually.
    """
    from folkseq.auth import build_youtube
    from googleapiclient.errors import HttpError

    essays = _load_essays()
    if not essays:
        print("No essays registered.")
        return

    pending = {ep: e for ep, e in essays.items() if not e.get("comment_posted")}
    if not pending:
        print("No pending comments.")
        return

    youtube = build_youtube()

    for episode, essay in sorted(pending.items()):
        video_id = _video_id_for_episode(episode)
        if not video_id:
            continue

        # Check privacy status
        r = youtube.videos().list(part="status", id=video_id).execute()
        if not r.get("items"):
            continue
        privacy = r["items"][0]["status"]["privacyStatus"]
        if privacy != "public":
            print(f"Episode {episode}: still {privacy} — skipping")
            continue

        try:
            youtube.commentThreads().insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": video_id,
                        "topLevelComment": {
                            "snippet": {
                                "textOriginal": f"{essay['comment']}\n\n{essay['url']}",
                            },
                        },
                    },
                },
            ).execute()
            essays[episode]["comment_posted"] = True
            _save_essays(essays)
            print(f"Episode {episode}: comment posted")
        except HttpError as e:
            print(f"Episode {episode}: comment FAILED — {e}")
