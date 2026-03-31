# Video Pipeline — Technical Reference

## Overview

```
Source .mov  -->  Transcode  -->  Thumbnail  -->  Upload  -->  Schedule
                  (ffmpeg)       (Gemini)        (YT API)    (publishAt)
```

## 1. Transcode

### Input
- Path: `/Volumes/Lacie/videos/folk-sequence/Folk Sequence NNN.mov`
- Format: H.264 Main, 4096x2328, ~60fps VFR, AAC-LC 100kbps

### ffmpeg Command
```bash
# Step 1: Probe duration for fade-out calculation
DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "Folk Sequence NNN.mov")

# Step 2: Transcode with fades baked in
ffmpeg -i "Folk Sequence NNN.mov" \
  -vf "crop=4096:2304:0:12,scale=3840:2160:flags=lanczos,fade=t=in:st=0:d=0.5,fade=t=out:st=${DURATION}-3:d=3" \
  -c:v libx264 -profile:v high -level 5.1 -preset slow \
  -b:v 35M -maxrate 40M -bufsize 80M \
  -r 60 -g 30 -bf 2 -flags +cgop \
  -pix_fmt yuv420p \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -af "loudnorm=I=-14:TP=-1:LRA=11,afade=t=in:st=0:d=0.5,afade=t=out:st=${DURATION}-3:d=3" \
  -c:a aac -b:a 384k -ar 48000 -ac 2 \
  -movflags +faststart \
  -y "folk-sequence-NNN.mp4"
```

### Processing Notes
- `crop=4096:2304:0:12` removes 12px from top and 12px from bottom to achieve 16:9
- `scale=3840:2160:flags=lanczos` scales to standard 4K UHD with high-quality resampling
- `fade=t=in:st=0:d=0.5` — 0.5s video fade from black (barely perceptible, smooths the hard cut)
- `fade=t=out:st=${DURATION}-3:d=3` — 3s video fade to black (graceful ending for music content)
- `afade` — matching audio fades (applied after loudnorm so levels are correct before fading)
- Duration is probed via ffprobe before encoding so fade-out timing is exact
- `-preset slow` for better compression efficiency (worth the time for uploads)
- `-b:v 35M` matches YouTube's recommended 4K SDR bitrate
- `-g 30` sets GOP to half the frame rate (30 frames at 60fps)
- `loudnorm=I=-14:TP=-1:LRA=11` normalizes audio to YouTube's -14 LUFS target with -1 dBTP ceiling
- `-movflags +faststart` moves moov atom to front for streaming

### Output
- Path: `output/folk-sequence-NNN.mp4`
- Expected size: ~3.9 GB for a 15-min video at 35 Mbps

## 2. Thumbnail Generation

### Process
1. Call Gemini Nano Banana 2 API with episode-specific prompt
2. Decode base64 PNG response
3. Resize to exactly 1280x720 with ImageMagick
4. Convert to JPEG at quality 95 (must be under 2 MB)
5. Analyze with Gemini, pick best of 3 candidates

### Output
- Path: `output/thumbnails/folk-sequence-NNN.jpg`
- Size: 1280x720, JPEG, < 2 MB

## 3. Upload

### YouTube Data API v3 Flow
1. Load OAuth 2.0 credentials (refresh token)
2. Build `youtube` service client
3. Create `videos.insert` request with:
   - `snippet.title`: "Folk Sequence NNN"
   - `snippet.description`: video description with jalopy.music link
   - `snippet.tags`: default tag set
   - `snippet.categoryId`: "10" (Music)
   - `status.privacyStatus`: "private" (for scheduled publishing)
   - `status.publishAt`: ISO 8601 datetime
   - `status.selfDeclaredMadeForKids`: false
4. Execute resumable upload with exponential backoff
5. Set thumbnail via `thumbnails.set`

### Quota Budget
- `videos.insert`: 1600 units
- `thumbnails.set`: 50 units
- Daily quota: 10,000 units
- Max uploads per day: ~6

## 4. Scheduling

### Logic
```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

central = ZoneInfo("America/Chicago")

def next_publish_time(start_date, episode_offset):
    """Calculate publish time for episode N days after start."""
    publish_date = start_date + timedelta(days=episode_offset)
    local_time = datetime(
        publish_date.year, publish_date.month, publish_date.day,
        15, 0, 0, tzinfo=central
    )
    return local_time.isoformat()
```

### DST Handling
- `America/Chicago` automatically handles CDT (UTC-5) and CST (UTC-6)
- 3:00 PM Central is always 3:00 PM local regardless of DST

## 5. Output Directory Structure

```
output/
  folk-sequence-001.mp4
  folk-sequence-002.mp4
  thumbnails/
    folk-sequence-001.jpg
    folk-sequence-002.jpg
  channel/
    profile.png      (800x800)
    banner.png       (2560x1440)
  logs/
    upload-001.json   (API response)
    upload-002.json
```
