# Gemini Image Generation Prompts

All prompts use model `gemini-3.1-flash-image-preview` (Nano Banana 2).

## Profile Picture (800x800)

### Generation Prompt
```
Generate a minimalist logo for a YouTube music channel called "Folk Sequence".
The design should be abstract and geometric — think sequencer grid patterns
merged with organic folk art motifs. Use a warm color palette: deep amber,
burnt orange, and cream on a dark background. The image should be iconic and
recognizable at small sizes. No text. Square format, clean edges.
```

### Config
```python
image_config=types.ImageConfig(aspect_ratio="1:1", image_size="1K")
```

### Analysis Prompt (fed back to Gemini with the generated image)
```
Analyze this image for use as a YouTube channel profile picture. Consider:
1. Readability at 98x98 pixels (minimum YouTube display size)
2. How it looks cropped to a circle
3. Visual distinctiveness and memorability
4. Color contrast and clarity
Score 1-10 and explain your reasoning.
```

## Channel Banner (2560x1440)

### Generation Prompt
```
Generate a wide panoramic banner for a YouTube channel called "Folk Sequence"
about music production in Bitwig Studio. The design should show an abstract
visualization of a music sequencer — rows of colored blocks and patterns that
suggest musical notes and rhythms, fading from left to right. Use warm amber
and orange tones against a dark charcoal background. The central area
(roughly the middle third) should be the focal point. Minimalist, modern,
no text. Aspect ratio 16:9.
```

### Config
```python
image_config=types.ImageConfig(aspect_ratio="16:9", image_size="2K")
```

### Analysis Prompt
```
Analyze this image for use as a YouTube channel banner. Consider:
1. Safe area: the center 1546x423 pixels must contain the main visual interest
2. How it looks on desktop (full width) vs mobile (center crop)
3. Whether it communicates "music production" at a glance
4. Color harmony and professionalism
Score 1-10 and explain your reasoning.
```

## Video Thumbnail (1280x720)

### Generation Prompt Template
```
Generate a YouTube thumbnail for a music production video titled
"Folk Sequence {NNN}". Show an abstract representation of a digital audio
workstation screen with colorful track lanes, MIDI notes, and waveforms.
Use a warm color palette with amber, orange, and teal accents on a dark
background. Include the text "{NNN}" in a large, bold, modern sans-serif
font in the lower-right corner. The style should be clean and recognizable
at small sizes.
```

### Config
```python
image_config=types.ImageConfig(aspect_ratio="16:9", image_size="1K")
```

### Analysis Prompt
```
Analyze this image for use as a YouTube video thumbnail. Consider:
1. Readability of the episode number at small sizes
2. Visual appeal and click-worthiness
3. Consistency with a series of numbered episodes
4. Contrast and clarity on both light and dark backgrounds
Score 1-10 and explain your reasoning.
```

## Iterative Refinement Process

For each asset, run 3 iterations:

```
Round 1: Generate 3 images from the base prompt
         -> Analyze each with Gemini
         -> Select best, note feedback

Round 2: Modify prompt based on Round 1 feedback
         -> Generate 3 more images
         -> Analyze each
         -> Compare with Round 1 best

Round 3: Final refinement based on Round 2 feedback
         -> Generate 3 final images
         -> Pick overall best across all rounds
```

The CLI `folkseq thumbnail` and `folkseq channel` commands implement this loop automatically.
