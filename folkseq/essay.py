"""Attach companion essays to Folk Sequence videos.

Each episode has a companion essay published as a markdown file in the
folk-sequence.github.io Jekyll site. This module:

- Publishes the essay to the Pages repo (commit + push), deriving the URL
- Updates the YouTube video description with the essay link
- Posts an owner comment with the link
- After upload, adds the YouTube link to the essay front matter and pushes

Comments cannot be posted on private/scheduled videos — those are queued
and posted automatically once the video goes public via --retry-pending.
"""

import json
import re
import subprocess
from pathlib import Path

OUTPUT_DIR = Path("output")
ESSAYS_PATH = OUTPUT_DIR / "logs" / "essays.json"
SCHEDULE_PATH = OUTPUT_DIR / "logs" / "schedule.json"

PAGES_REPO = Path.home() / "vibe" / "folk-sequence.github.io"
PAGES_SITE_URL = "https://folk-sequence.github.io"


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


def _slugify(text):
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def _essay_basename(episode, title):
    return f"{episode}-{_slugify(title)}"


def _essay_path(episode, title):
    return PAGES_REPO / f"{_essay_basename(episode, title)}.md"


def _essay_url(episode, title):
    return f"{PAGES_SITE_URL}/{_essay_basename(episode, title)}/"


def _yaml_quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _strip_leading_title(body):
    """Strip a leading H1 and any subtitle/italic line + blank lines."""
    lines = body.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].lstrip().startswith("# "):
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and (lines[i].startswith("*") or "companion essay" in lines[i].lower()):
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    return "\n".join(lines[i:]).strip() + "\n"


def _git_commit_push(message):
    """Commit whatever is staged in PAGES_REPO and push to origin/main."""
    subprocess.run(["git", "-C", str(PAGES_REPO), "commit", "-q", "-m", message], check=True)
    subprocess.run(["git", "-C", str(PAGES_REPO), "push", "origin", "main"], check=True, capture_output=True)


def publish_essay_to_pages(episode, title, topic, source_file):
    """Copy a source markdown file into the Pages repo with front matter, commit, push.

    Returns the published essay URL.
    """
    if not PAGES_REPO.exists():
        raise SystemExit(f"Pages repo not found at {PAGES_REPO}")

    src = Path(source_file)
    if not src.exists():
        raise SystemExit(f"Essay file not found: {src}")

    body = _strip_leading_title(src.read_text())

    fm = "\n".join([
        "---",
        "layout: essay",
        f"title: {_yaml_quote(title)}",
        f'episode: "{episode}"',
        f"topic: {_yaml_quote(topic)}",
        f"description: {_yaml_quote(title + ' — companion essay for Folk Sequence ' + episode)}",
        "---",
        "",
        "",
    ])

    dest = _essay_path(episode, title)
    dest.write_text(fm + body)

    subprocess.run(["git", "-C", str(PAGES_REPO), "add", dest.name], check=True)
    _git_commit_push(f"Add essay {episode}: {title}")

    url = _essay_url(episode, title)
    print(f"  Essay published: {url}")
    return url


def attach_video_link_to_essay(episode, video_id):
    """Add a `youtube:` field to the essay front matter and push.

    Idempotent — if the YouTube link is already present, does nothing.
    Called by `folkseq upload` after a successful upload.
    """
    essays = _load_essays()
    essay = essays.get(episode)
    if not essay:
        print(f"  No essay registered for episode {episode} — skipping essay update")
        return

    title = essay.get("title", "")
    if not title:
        print(f"  No title for episode {episode} — skipping essay update")
        return

    path = _essay_path(episode, title)
    if not path.exists():
        print(f"  Essay markdown not found at {path} — skipping")
        return

    youtube_url = f"https://youtu.be/{video_id}"
    content = path.read_text()
    if youtube_url in content:
        print(f"  Essay already has YouTube link — skipping")
        return

    lines = content.splitlines()
    new_lines = []
    in_fm = False
    seen_first_fence = False
    inserted = False
    for line in lines:
        if line.strip() == "---":
            if not seen_first_fence:
                seen_first_fence = True
                in_fm = True
                new_lines.append(line)
                continue
            if in_fm and not inserted:
                new_lines.append(f'youtube: "{youtube_url}"')
                inserted = True
            in_fm = False
            new_lines.append(line)
            continue
        if in_fm and line.startswith("youtube:"):
            continue
        new_lines.append(line)

    path.write_text("\n".join(new_lines) + ("\n" if content.endswith("\n") else ""))

    try:
        subprocess.run(["git", "-C", str(PAGES_REPO), "add", path.name], check=True, capture_output=True)
        _git_commit_push(f"Add YouTube link to {path.name}")
        print(f"  Essay updated with YouTube link and pushed")
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode() if getattr(e, "stderr", None) else ""
        print(f"  Essay git push FAILED: {err[:200]}")


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


def add_essay(episode, url, title, comment, topic=None, tags=None, source_file=None):
    """Register an essay for an episode and apply it to YouTube.

    Idempotent. Safe to re-run.

    Args:
        episode: Episode number string (e.g., "001").
        url: Public essay URL (folk-sequence.github.io/NNN-slug/). If
            source_file is also given, this is ignored and the URL is
            derived from the title after publishing to the Pages repo.
        title: Essay title (used in description block).
        comment: Comment text (used in description and YouTube comment).
        topic: Short SEO topic phrase used in the video title:
            "Folk Sequence NNN — {topic}". REQUIRED for upload to work.
        tags: List of per-episode tags appended to the global base tags.
        source_file: Optional path to a raw markdown essay. If provided,
            the essay is committed to the Pages repo with front matter
            and the derived URL is used.
    """
    from folkseq.auth import build_youtube
    from googleapiclient.errors import HttpError

    if source_file:
        if not topic:
            print("ERROR: --topic is required when publishing a new essay from --file")
            raise SystemExit(1)
        url = publish_essay_to_pages(episode, title, topic, source_file)

    essays = _load_essays()
    existing = essays.get(episode, {})
    essays[episode] = {
        "title": title,
        "url": url,
        "comment": comment,
        "topic": topic if topic is not None else existing.get("topic"),
        "tags": tags if tags is not None else existing.get("tags", []),
        "comment_posted": existing.get("comment_posted", False),
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
                            "textOriginal": f"{gist_url} {comment}",
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
                                "textOriginal": f"{essay['url']} {essay['comment']}",
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
