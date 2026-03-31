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

## Video Encoding Settings (ffmpeg)

```bash
# Probe duration first (needed for fade-out calculation)
DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 input.mov)

ffmpeg -i input.mov \
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

### Fade Settings

- **Fade in**: 0.5s video + audio (barely perceptible, smooths the hard cut)
- **Fade out**: 3s video + audio (graceful ending, standard for music content)
- Fades are baked into the transcode step — no extra step required
- Duration is probed via ffprobe before encoding so fade-out timing is exact

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

- One video per day at 3:00 PM US Central Time
- CDT (Mar-Nov): UTC-5 -> 20:00 UTC
- CST (Nov-Mar): UTC-6 -> 21:00 UTC
- Rationale: 2-3 hours before peak viewing (6-9 PM) gives algorithm time to index and ramp distribution
- Use `zoneinfo.ZoneInfo("America/Chicago")` for automatic DST handling

## Video Naming Convention

- Source: `Folk Sequence NNN.mov` (NNN = zero-padded 3 digits)
- Output: `folk-sequence-NNN.mp4`
- YouTube title: `Folk Sequence NNN`

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

## Dependencies

- **System**: ffmpeg, ffprobe, magick (ImageMagick)
- **Python** (via uv): google-api-python-client, google-auth-oauthlib, google-genai

## Security

- **NEVER** commit API keys, OAuth tokens, or secrets
- `.env` files are in `.gitignore`
- OAuth token files are in `.gitignore`
- This is a public repository
