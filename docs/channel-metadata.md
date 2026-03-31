# Folk Sequence — YouTube Channel Metadata

## Channel Settings

| Field | Value | Chars | Limit |
|-------|-------|-------|-------|
| Name | Folk Sequence | 13 | 100 |
| Handle | @FolkSequence | — | — |
| URL | https://www.youtube.com/@FolkSequence | — | — |
| Link URL | https://jalopy.music/ | — | — |

## Channel Description (200/1000 chars)

```
Screen recordings of music creation in Bitwig Studio. Each episode captures a full session building a new track from scratch. No narration, no edits — just the creative process.

https://jalopy.music/
```

## Default Video Title Pattern (17/100 chars)

```
Folk Sequence 001
```

## Default Video Description (82/5000 chars)

```
A screen recording session creating music in Bitwig Studio.

https://jalopy.music/
```

## Default Video Tags (99/500 chars)

```
bitwig,bitwig studio,music production,screen recording,daw,electronic music,folk,ambient,generative
```

## Visual Assets

### Profile Picture (800x800, displayed as circle)

**Gemini Prompt:**
```
Generate a minimalist logo for a YouTube music channel called "Folk Sequence".
The design should be abstract and geometric — think sequencer grid patterns
merged with organic folk art motifs. Use a warm color palette: deep amber,
burnt orange, and cream on a dark background. The image should be iconic and
recognizable at small sizes. No text. Square format, clean edges.
```

### Channel Banner (2560x1440, safe area 1546x423 centered)

**Gemini Prompt:**
```
Generate a wide panoramic banner for a YouTube channel called "Folk Sequence"
about music production in Bitwig Studio. The design should show an abstract
visualization of a music sequencer — rows of colored blocks and patterns that
suggest musical notes and rhythms, fading from left to right. Use warm amber
and orange tones against a dark charcoal background. The central area
(roughly the middle third) should be the focal point. Minimalist, modern,
no text. Aspect ratio 16:9.
```

### Video Thumbnail (1280x720)

**Gemini Prompt Template:**
```
Generate a YouTube thumbnail for a music production video titled
"Folk Sequence {NNN}". Show an abstract representation of a digital audio
workstation screen with colorful track lanes, MIDI notes, and waveforms.
Use a warm color palette with amber, orange, and teal accents on a dark
background. Include the text "{NNN}" in a large, bold, modern sans-serif
font in the lower-right corner. The style should be clean and recognizable
at small sizes.
```

## Asset Generation Pipeline

For each asset type, generate 3 candidates:
1. Generate image with Gemini Nano Banana 2
2. Post-process with ImageMagick (resize, ensure exact dimensions)
3. Feed back to Gemini for analysis ("Rate this image for use as a YouTube {asset type}. Score 1-10 and explain.")
4. Pick the highest-scored candidate
5. Save final asset

### ImageMagick Post-Processing

```bash
# Profile picture: ensure 800x800, PNG
magick input.png -resize 800x800! -gravity center profile.png

# Banner: ensure 2560x1440, PNG
magick input.png -resize 2560x1440! banner.png

# Thumbnail: ensure 1280x720, JPG for size
magick input.png -resize 1280x720! -quality 95 thumbnail.jpg
```
