# CLAUDE.md — Folk Sequence YouTube Pipeline

## Project Overview

Automated pipeline for processing and uploading Bitwig Studio screen recordings to YouTube.

- **Channel**: Folk Sequence (@FolkSequence)
- **URL**: https://www.youtube.com/@FolkSequence
- **Website**: https://jalopy.music/
- **Content**: Screen recordings of music creation in Bitwig Studio — no narration, no edits
- **Source videos**: `/Volumes/Lacie/videos/bitwig-folk/Folk Sequence NNN.mov`
- **Note**: Video 000 (`Bitwig Folk 000.mov`) exists but will not be posted (screen recording mistake). Series starts at 001.

## Pipeline Steps

1. **Transcode** source `.mov` to YouTube-optimized `.mp4` using ffmpeg
2. **Generate thumbnail** using Gemini Nano Banana 2 image generation API
3. **Upload** to YouTube via Data API v3 with scheduled publish time
4. **Schedule** one video per day at 7:30 AM US Central (CDT: UTC-5 / CST: UTC-6)

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
| `schedule` | Schedule next N videos for daily upload at 7:30 AM Central |
| `status` | Show pipeline status for all videos |
| `channel` | Generate/update channel metadata assets |

## Video Encoding Settings (ffmpeg)

```bash
ffmpeg -i input.mov \
  -vf "crop=4096:2304:0:12,scale=3840:2160" \
  -c:v libx264 -profile:v high -preset slow \
  -b:v 35M -maxrate 40M -bufsize 80M \
  -r 60 -g 30 -bf 2 \
  -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -c:a aac -b:a 384k -ar 48000 -ac 2 \
  -movflags +faststart \
  -y output.mp4
```

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

- One video per day at 7:30 AM US Central Time
- CDT (Mar-Nov): UTC-5 -> 12:30 UTC
- CST (Nov-Mar): UTC-6 -> 13:30 UTC
- Use `zoneinfo.ZoneInfo("America/Chicago")` for automatic DST handling

## Video Naming Convention

- Source: `Folk Sequence NNN.mov` (NNN = zero-padded 3 digits)
- Output: `folk-sequence-NNN.mp4`
- YouTube title: `Folk Sequence NNN`

## Channel Metadata

- **Name**: Folk Sequence (13/100 chars)
- **Handle**: @FolkSequence
- **Description** (200/1000 chars):
  > Screen recordings of music creation in Bitwig Studio. Each episode captures a full session building a new track from scratch. No narration, no edits — just the creative process.
  >
  > https://jalopy.music/
- **Link URL**: https://jalopy.music/

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
