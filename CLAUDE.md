# CLAUDE.md — Folk Sequence YouTube Pipeline

## Project Overview

Automated pipeline for processing and uploading Bitwig Studio screen recordings to YouTube.

- **Channel**: Folk Sequence (@FolkSequence)
- **URL**: https://www.youtube.com/@FolkSequence
- **Website**: https://jalopy.music/
- **Content**: Screen recordings of music creation in Bitwig Studio — no narration, no edits
- **Source videos**: `/Volumes/Lacie/videos/folk-sequence/Folk Sequence NNN.mov`
- **Note**: Video 000 (`Bitwig Folk 000.mov`) exists but will not be posted (screen recording mistake). Series starts at 001.

## Pipeline Steps

1. **Transcode** source `.mov` to YouTube-optimized `.mp4` using ffmpeg
2. **Generate thumbnail** using Gemini Nano Banana 2 image generation API
3. **Upload** to YouTube via Data API v3 with scheduled publish time
4. **Schedule** one video per day at 3:00 PM US Central (CDT: UTC-5 / CST: UTC-6)

## CLI Tool: `folkseq`

Single unified CLI built with Python (uv). Usage pattern:

```
folkseq <command> [command-args] [-- wrapped-command-args]
folkseq --help
folkseq <command> --help
```

### Commands

| Command | Description |
|---------|-------------|
| `transcode` | Convert source .mov to YouTube-optimized .mp4 |
| `thumbnail` | Generate thumbnail using Gemini image generation |
| `upload` | Upload video to YouTube with metadata and thumbnail |
| `schedule` | Schedule next N videos for daily upload at 3:00 PM Central |
| `status` | Show pipeline status for all videos |
| `channel` | Generate/update channel metadata assets |
| `essay` | Publish companion essay, patch YouTube description, post comment |
| `substack` | Publish to folksequence.substack.com via Playwright |
| `patreon` | Publish to patreon.com/cw/FolkSequence via Playwright |
| `jalopy` | Add final mix MP3 to jalopy.music (skewer-case R2+D1) |

## Video Encoding Settings (ffmpeg)

```bash
# Probe duration first (needed for fade-out calculation)
DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 input.mov)
# Cap at 14:59 (899s) — trim from end if longer
if [ $(echo "$DURATION > 899" | bc) -eq 1 ]; then DURATION=899; fi

ffmpeg -i input.mov \
  -t ${DURATION} \
  -vf "crop=4096:2304:0:12,scale=3840:2160,fade=t=in:st=0:d=0.5,fade=t=out:st=${DURATION}-3:d=3" \
  -c:v libx264 -profile:v high -preset slow \
  -b:v 35M -maxrate 40M -bufsize 80M \
  -r 60 -g 30 -bf 2 \
  -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -af "loudnorm=I=-14:TP=-1:LRA=11,afade=t=in:st=0:d=0.5,afade=t=out:st=${DURATION}-3:d=3" \
  -c:a aac -b:a 384k -ar 48000 -ac 2 \
  -movflags +faststart \
  -y output.mp4
```

### Max Duration

- **Hard cap**: 14 minutes 59 seconds (899s). Videos longer than this are trimmed from the end.
- Always starts at 0:00 — the beginning of the session is never cut.
- Fades are applied at the trimmed end, so the fade-out is always clean.

### Fade Settings

- **Fade in**: 0.5s video + audio (barely perceptible, smooths the hard cut)
- **Fade out**: 3s video + audio (graceful ending, standard for music content)
- Fades are baked into the transcode step — no extra step required
- Duration is probed via ffprobe before encoding so fade-out timing is exact

### Intro Lead-In (Episode 019+)

Every episode (starting 019) opens with a 7-second lead-in from a **universal intro clip** (no audio), overlaid with the **current episode's WAV audio** for those 7 seconds. At t=7s, a 1-second xfade/acrossfade transitions into the current .mov. The first 7 seconds of the current .mov are discarded.

- **Intro clip**: `output/intro-all-episodes-no-audio.mp4` — 7s video, no audio, 3840×2160, 60fps H.264
- **Intro clip source**: Extracted once from episode 018's .mov. Reused for ALL future episodes.
- **WAV audio**: `/Volumes/Lacie/masters/folk-sequence/Folk Sequence NNN.wav` (current episode WAV provides audio for intro segment)
- **Auto-detection**: `folkseq transcode` auto-looks for `output/intro-all-episodes-no-audio.mp4` and `Folk Sequence NNN.wav`. Falls back to simple transcode if either missing.
- **Crossfade**: 1s xfade (video) + acrossfade (audio) at the 7s junction

### Upload Timeout & Recovery

**Uploads take 5-15 minutes** (1.3 GB file, resumable upload). Bash tool timeout (300s) often fires before completion.
- **Always use `--timeout 600` minimum** on `folkseq upload` bash calls
- Upload code writes `video_id` to `output/logs/video-id-NNN.txt` immediately after YouTube returns it — even if the caller times out, the ID is on disk
- If upload completes but `schedule.json` never got the `video_id`: `folkseq upload-recover NNN` — searches YouTube by title, patches schedule.json
- Manual recovery: find video ID in YouTube Studio URL, then edit `schedule.json` to add `"video_id": "<ID>"`

### Re-upload Procedure

YouTube does not allow replacing a video file. To fix an already-uploaded episode:
1. Delete the old video: `youtube.videos().delete(id=VIDEO_ID)`
2. Clear `video_id` in `schedule.json` (keep the schedule entry and publish time)
3. Re-transcode from the original .mov
4. Re-upload with `folkseq upload NNN` — picks up existing schedule entry and thumbnail

**022 re-upload (2026-04-22)**: First upload video_id `-qSiKSiDOIs` timed out (client never got response). Video was live but schedule.json had stale ID. Brian re-uploaded manually → new ID `o3AjcVkZ3c8`. Updated schedule.json to match.

### Source Video Stats (Folk Sequence 000.mov)

- Resolution: 4096x2328 (non-standard, needs crop+scale)
- Codec: H.264 Main, ~4.2 Mbps, ~60fps VFR, yuv420p BT.709
- Audio: AAC-LC, 48kHz stereo, 100 kbps
- Duration: ~24 min, Size: ~750 MB

### Target YouTube Specs

- Resolution: 3840x2160 (4K UHD, 16:9)
- Codec: H.264 High Profile, 35 Mbps CBR, 60fps CFR
- Audio: AAC-LC, 48kHz stereo, 384 kbps
- Container: MP4 with faststart

## YouTube API

- Uses YouTube Data API v3 via `google-api-python-client`
- OAuth 2.0 with offline refresh token for headless operation
- Resumable uploads (critical for large files)
- Each upload costs 1600 quota units (default daily quota: 10,000 = ~6 uploads/day)
- Scheduling: set `status.publishAt` (ISO 8601) + `privacyStatus: "private"`

## Scheduling Logic

- One video per day, 7 days a week, at 3:00 PM US Central Time
- CDT (Mar-Nov): UTC-5 -> 20:00 UTC
- CST (Nov-Mar): UTC-6 -> 21:00 UTC
- Rationale: 2-3 hours before peak viewing (6-9 PM) gives algorithm time to index and ramp distribution
- Use `zoneinfo.ZoneInfo("America/Chicago")` for automatic DST handling
- **Same-day publishing**: If the queue is empty and it's before 2:00 PM Central, schedule for today. Otherwise, schedule for tomorrow. The 1-hour buffer gives YouTube time to process 4K.
- **Queue behavior**: If the queue has entries, always append to the back (next day after last scheduled). Never replace or reorder existing entries.
- Brian may record multiple videos per day or skip days — the queue absorbs the variance

## Video Naming Convention

- Source: `Folk Sequence NNN.mov` (NNN = zero-padded 3 digits)
- Output: `folk-sequence-NNN.mp4`
- YouTube title: `Folk Sequence NNN`

## Face Cutout Compositing

- **Source**: `output/faces/` — ~45 PNG cutouts with transparent backgrounds
- **Cycling**: Sequential by episode number, wraps around: `cutouts[(episode - 1) % len(cutouts)]`
- **Thumbnail placement**: Bottom edge, left side. X varies per episode: `(episode * 137) % 320 + 80` pixels from left. Face height: 320px.
- **Banner**: One cutout composited onto channel banner at bottom-right (`SouthEast +300+0`, 600px tall)
- **Pipeline**: `folkseq thumbnail` automatically composites a face after generating the base image. Base saved as `-base.jpg`, final with face as `.jpg`.
- **In-place updates**: `thumbnails.set` API can update thumbnails on both public and private videos without affecting any other metadata (title, description, publish date, privacy status).

## Companion Essays

Every episode has a companion essay published on the [folk-sequence.github.io](https://folk-sequence.github.io) Jekyll site (repo: `folk-sequence/folk-sequence.github.io`, locally cloned at `~/vibe/folk-sequence.github.io`). Each essay is a markdown file at repo root named `NNN-slug.md` with Jekyll front matter (`layout: essay`, `title`, `episode`, `topic`, `youtube`, `description`) and renders at `https://folk-sequence.github.io/NNN-slug/`. Essays are long-form prose suitable for Speechify TTS (no headers, no lists, no tables, flowing paragraphs of varied length). The essay link goes in two places: the video description (always) and a top-level comment from the channel owner (post-publish).

**Voice rules** (derived from Brian's writing on lluminate.substack.com):
- First principles derivation, not prescription. Trace concepts to underlying truths.
- Differentiate concepts from similar ideas AND their opposites — explicit contrast.
- Expose unstated assumptions and axioms in conventional wisdom; build unique value from there.
- Opinionated, edgy, take sides. Convictions stated plainly without hedging.
- Avoid jargon; spell out acronyms on first use.
- Vary sentence and paragraph length naturally — no bursts of short punchy sentences, no one-sentence paragraphs.
- No section headers, no lists, no tables, no diagrams. Title at top only. Flowing prose only.
- Use "the X" abstractions for clean reference (e.g. "the producer", "the listener").
- Each essay must be unique and specific. If someone reads all essays back to back, no point should be redundant.
- Web search to capture the moment (Bitwig releases, music industry news, scene shifts).

**Format**: Description footer template appends `Companion essay: TITLE\nURL\n\nCOMMENT\n\njalopy.music`. The same comment text + URL is posted as a top-level comment via `commentThreads.insert`.

**Algorithm safety**: `videos().update()` on description does NOT trigger re-upload behavior or affect publish date. Confirmed safe via API docs and testing. Pinning comments must be done manually in YouTube Studio (no API for it). Comment bodies on public videos can be edited in place via `comments().update()` when the channel owns the comment — useful for retroactive URL fixes.

**Comments on private videos fail**: Scheduled-private videos cannot accept comments. Use `folkseq essay --retry-pending` to post queued comments after each video goes public. Run it daily after 3:00 PM Central, or set up a cron job.

**Commands**:
- `folkseq essay NNN --file /tmp/essay.md --title "..." --topic "..." --tags "..." --comment "..."` — publishes the essay to the Pages repo (commit + push), derives the URL, registers in essays.json, patches YouTube description, attempts comment
- `folkseq essay NNN --url URL --title "..." --comment "..."` — register essay without publishing (when the markdown is already in the Pages repo)
- `folkseq essay --retry-pending` — retry failed comments for any videos that are now public
- State stored in `output/logs/essays.json`

**Per-episode workflow** (in order):
1. Record `Folk Sequence NNN.mov` in Bitwig (WAV master auto-saved to `/Volumes/Lacie/masters/folk-sequence/`)
2. `folkseq transcode "/Volumes/Lacie/videos/folk-sequence/Folk Sequence NNN.mov"` — auto-uses intro clip from prev episode + current WAV if both exist; extracts this episode's intro clip afterward
3. `folkseq thumbnail NNN`
4. Write essay to `/tmp/folk-sequence-NNN-slug.md` (no front matter needed — just the H1 title + body)
5. `folkseq essay NNN --file /tmp/folk-sequence-NNN-slug.md --title "..." --topic "..." --tags "tag1,tag2,tag3" --comment "..."` — publishes the essay to `folk-sequence.github.io` (commit + push), derives the URL, registers essay with SEO metadata, updates YouTube description
6. `folkseq schedule --days 1`
7. `folkseq upload NNN` — REQUIRES the essay (with `topic`) to exist. Hard-fails otherwise. Title becomes `Folk Sequence NNN — {topic}`. Description leads with a keyword-rich opener and includes the essay block. Tags = global base tags + per-episode tags. After successful upload, automatically updates the essay front matter in the Pages repo to add `youtube: "https://youtu.be/VIDEO_ID"` and pushes.
8. `folkseq substack NNN --schedule "YYYY-MM-DDTHH:MM:00-05:00"` — publishes to folksequence.substack.com (Patreon link → HR → YouTube embed → HR → essay). Schedule 15 min after YouTube (3:15 PM CDT = `T15:15:00-05:00`).
9. After 3 PM publish: cron loop posts the comment automatically (must be running)
10. Manually pin the comment in YouTube Studio

**Post-publish (always, in order):**
11. `folkseq essay NNN --retry-pending` — post companion essay comment after video goes public
12. `folkseq jalopy NNN --file /path/to/final-mix.mp3` — add final song to jalopy.music (surgical R2 upload + D1 INSERT)
13. Update folk-sequence.github.io homepage if not auto-added (add `<li>` entry at top of episode list in `index.md`, commit + push)
14. `folkseq patreon NNN --schedule "YYYY-MM-DDTHH:MM:00-05:00"` — publish to Patreon (YouTube embed → essay)

**Substack post format (verified 2026-04-20, episode 019):
- Centered Patreon link → `horizontal_rule` → `youtube2` embed → `horizontal_rule` → essay paragraphs
- Audience: `everyone` (free, not paywalled)
- Title: `Folk Sequence NNN — {essay_title}`
- Subtitle: `{topic}` from essays.json
- No hero image in body (YouTube embed is the visual)
- `folkseq/substack.py` — impl; `folkseq substack NNN --schedule ISO8601`
- Schedule 15 min after YouTube publish to ensure video is live before email sends
- SUBSTACK_SID cookie required in `~/.config/.env`
- Navigation after Send click = success (Substack redirects); verified via `/api/v1/post_management/scheduled`

**SEO conventions** (encoded in `folkseq/upload.py`):
- **Title**: `Folk Sequence NNN — {topic}` (keep topic short — total title under 70 chars)
- **Tags**: 15 global base tags (bitwig, bitwig studio, bitwig 6, folk, folktronica, ambient folk, alt country, americana, electronic folk, music production no talking, bitwig session, daw walkthrough, no narration, screen recording, folk music production) + per-episode `tags` from essays.json
- **Description opener**: `Folk Sequence NNN — {topic}. A folktronica and folk music production session in Bitwig Studio 6, recorded as a continuous take with no narration, no edits, and no cuts. Part of a daily series.` followed by the essay block

`folkseq upload` will refuse to run if no essay is registered for the episode. This is intentional — every video must ship with its companion essay.

## jalopy.music (Folk Sequence songs)

**Platform**: [skewer-case](https://github.com/bedwards/skewer-case) — personal music streaming site (React + Vite + Hono + Cloudflare Workers/D1/R2). Folk Sequence is one of several artists on the platform. Folk Sequence tracks live under `folk-sequence/vol-1`, `folk-sequence/vol-2`, etc.

**Data locations**:
- **Source WAV**: `/Volumes/Lacie/masters/folk-sequence/Folk Sequence NNN.wav` (Bitwig master — WAV only, NO pre-existing MP3)
- **skewer-case repo**: `~/vibe/skewer-case` (Bun/TypeScript CLI)
- **Data root**: `/Volumes/External/skewer-case-data/folk-sequence/vol-N/` (metadata.json + MP3s)
- **Cloudflare**: R2 bucket `skewer-case-media`, D1 database `skewer-case-db`

**MP3 creation + surgical upload (safe, one track only):**
1. Convert WAV → MP3: `cd ~/vibe/skewer-case && bun run add -- /Volumes/Lacie/masters/folk-sequence/`
   - Scans dir, converts WAV→320kbps MP3 via ffmpeg, copies to `/Volumes/External/skewer-case-data/unclassified/`
   - Generates fingerprints, extracts metadata, creates/updates metadata.json in unclassified
2. Move MP3 to album dir: `cp /Volumes/External/skewer-case-data/unclassified/unclassified/folk-sequence-NNN.mp3 /Volumes/External/skewer-case-data/folk-sequence/vol-N/NN-slug.mp3`
3. Update `metadata.json` in the album dir — add track entry (title, slug, trackNumber, duration)
4. Surgical upload (one file, safe): `cd ~/vibe/skewer-case && bun run upload -- --file /Volumes/External/skewer-case-data/folk-sequence/vol-N/NN-slug.mp3 --artist "Folk Sequence" --album "Vol N" --title "Title (NNN)"`
   - Uploads to R2, INSERTs into D1, updates album track_count
   - Does NOT touch other tracks. Does NOT re-index. Does NOT delete anything.

**Album dir upload (missing tracks only, safe):**
- `cd ~/vibe/skewer-case && bun run upload -- --album-dir /Volumes/External/skewer-case-data/folk-sequence/vol-N`
- Scans metadata.json, uploads only tracks NOT already in D1

**Full catalog wipe (DANGEROUS — requires flag + interactive confirm):**
- `cd ~/vibe/skewer-case && bun run upload -- --dangerously-delete`
- Requires typing "yes" at the terminal prompt
- Deletes ALL artists/albums/tracks from D1, re-uploads EVERYTHING to R2

## folk-sequence.github.io homepage

After publishing an essay, ensure it appears on the homepage. The essay markdown is auto-pushed by `folkseq essay`, but the homepage `index.md` requires a manual entry:
- Add `<li><a href="/NNN-slug/">` at top of `<ul class="episode-list">` in `~/vibe/folk-sequence.github.io/index.md`
- `git add index.md && git commit && git push`
- Future: automate this in `folkseq essay`

## Patreon publishing

- **URL**: https://www.patreon.com/cw/FolkSequence
- **Method**: Playwright browser automation (no official API for creating posts)
- **PATREON_SESSION cookie** required in `~/.config/.env`
- **Command**: `folkseq patreon NNN --schedule "YYYY-MM-DDTHH:MM:00-05:00"`
- **Post format**: YouTube embed → essay text → jalopy.music link
- **Schedule**: 30 min after YouTube publish (3:30 PM CDT) — Patreon scheduling is limited, may need manual publish
- Patreon has no native post scheduling. Posts go live immediately. Use Playwright to open browser at scheduled time, create post, click publish. Alternative: prepare draft manually, publish at time.
- `folkseq/patreon.py` — impl; similar to substack.py

## Channel Metadata

- **Name**: Folk Sequence (13/100 chars)
- **Handle**: @FolkSequence
- **Description** (179/1000 chars):
  > Screen recordings of music creation in Bitwig Studio. Each episode captures a full session building a new track from scratch. No narration, no edits — just the creative process.
- **Link URL** (channel link field): https://jalopy.music/

## Gemini Image Generation

- Model: `gemini-3.1-flash-image-preview` (Nano Banana 2)
- API key location: `~/.config/.env` (NEVER commit this)
- Used for: thumbnails (1280x720), channel banner (2560x1440), profile pic (800x800)

## Monetization

### YouTube Partner Program (pending)

- **Ads**: Pre-roll only. No mid-roll, no post-roll.
- **Channel Memberships** (Join button): Enabled. No perks.
- **No Shorts**: Not creating Shorts.
- `folkseq status` shows YTP progress.

### Patreon

- **URL**: https://www.patreon.com/cw/FolkSequence
- **No native scheduling** — posts go live on publish
- Posts via Playwright automation (like Substack)
- Session cookie in `~/.config/.env`

### Substack

- folksequence.substack.com — automated via `folkseq substack`

## jalopy.music / skewer-case MP3 workflow

**Process:**
1. `cd ~/vibe/skewer-case && bun run cli/src/add-songs.ts /Volumes/Lacie/masters/folk-sequence/` — converts WAV→320kbps MP3, copies to `/Volumes/External/skewer-case-data/unclassified/`
2. `cp /Volumes/External/skewer-case-data/unclassified/unclassified/folk-sequence-NNN.mp3 /Volumes/External/skewer-case-data/folk-sequence/vol-N/NN-slug.mp3`
3. Update `metadata.json` in album dir — add track entry (title, slug, trackNumber, duration)
4. `cd ~/vibe/skewer-case/cli && bun run src/upload-catalog.ts -- --file /Volumes/External/skewer-case-data/folk-sequence/vol-N/NN-slug.mp3 --artist "Folk Sequence" --album "Vol N" --title "Title (NNN)"` — surgical R2+D1
5. Site updates live — API reads D1 directly, no redeploy needed

**Known bug in `uploadSingleFile`:** If album doesn't exist yet in D1, it creates the album with `track_count=0`, then queries `track_count` to determine track_number → always gets 1. Fix manually: `UPDATE tracks SET track_number = N WHERE id = '...'`.

**Deploy to jalopy.music:** Push to `main` on `~/vibe/skewer-case`. GitHub Actions (`.github/workflows/deploy.yml`) deploys API Worker + Pages automatically.

## Dependencies

- **System**: ffmpeg, ffprobe, magick (ImageMagick)
- **Python** (via uv): google-api-python-client, google-auth-oauthlib, google-genai

## Security

- **NEVER** commit API keys, OAuth tokens, or secrets
- `.env` files are in `.gitignore`
- OAuth token files are in `.gitignore`
- This is a public repository
