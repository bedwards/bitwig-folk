# Folk Sequence — Bitwig YouTube Pipeline

Automated pipeline for processing Bitwig Studio screen recordings and uploading them to YouTube.

**Channel**: [Folk Sequence](https://www.youtube.com/@FolkSequence)
**Website**: [jalopy.music](https://jalopy.music/)

## What This Does

1. **Transcodes** raw screen recordings (`.mov`) to YouTube-optimized 4K `.mp4`
2. **Generates thumbnails** using Gemini AI image generation
3. **Uploads** to YouTube with metadata, thumbnail, and scheduled publish time
4. **Schedules** one video per day at 7:30 AM Central Time

## Prerequisites

- macOS with Homebrew
- Python 3.13+ via [uv](https://github.com/astral-sh/uv)
- ffmpeg, ImageMagick (`brew install ffmpeg imagemagick`)
- Google Cloud project with YouTube Data API v3 enabled
- Gemini API key in `~/.config/.env`

## Setup

```bash
# Clone and install
git clone git@github.com:bedwards/bitwig-folk.git
cd bitwig-folk
uv sync

# Authenticate with YouTube (one-time)
uv run folkseq auth

# Verify tools
uv run folkseq doctor
```

## Usage

```bash
# Transcode a video for YouTube
uv run folkseq transcode "/Volumes/Lacie/videos/bitwig-folk/Folk Sequence 001.mov"

# Generate a thumbnail
uv run folkseq thumbnail 001

# Upload with scheduling
uv run folkseq upload 001

# Schedule next 7 days of uploads
uv run folkseq schedule --days 7

# Check pipeline status
uv run folkseq status
```

## Pipeline Details

### Video Processing

Source recordings from Bitwig Studio are 4096x2328 ~60fps H.264 `.mov` files. The pipeline:

- Crops to 16:9 aspect ratio (4096x2304)
- Scales to 3840x2160 (4K UHD)
- Encodes H.264 High Profile at 35 Mbps, constant 60fps
- Encodes audio AAC-LC 384 kbps stereo 48kHz
- Outputs MP4 with faststart for streaming

### Thumbnail Generation

Uses Google Gemini Nano Banana 2 (`gemini-3.1-flash-image-preview`) to generate 1280x720 thumbnails. Three candidates are generated per video, analyzed, and the best is selected.

### YouTube Upload

Uses YouTube Data API v3 with resumable uploads. Videos are uploaded as private and scheduled to publish at 7:30 AM Central Time, one per day.

## Video Naming

| Component | Format | Example |
|-----------|--------|---------|
| Source file | `Folk Sequence NNN.mov` | `Folk Sequence 001.mov` |
| Output file | `folk-sequence-NNN.mp4` | `folk-sequence-001.mp4` |
| YouTube title | `Folk Sequence NNN` | `Folk Sequence 001` |

## License

MIT
