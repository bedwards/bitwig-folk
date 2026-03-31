"""Generate YouTube thumbnails using Gemini image generation."""

import os
import re
import subprocess
from pathlib import Path

from google import genai
from google.genai import types

OUTPUT_DIR = Path("output/thumbnails")

GENERATION_PROMPT = """\
Generate a YouTube thumbnail for a music production video titled
"Folk Sequence {episode}". Show an abstract representation of a digital audio
workstation screen with colorful track lanes, MIDI notes, and waveforms.
Use a warm color palette with amber, orange, and teal accents on a dark
background. Include the text "{episode}" in a large, bold, modern sans-serif
font in the lower-right corner. The style should be clean and recognizable
at small sizes."""

ANALYSIS_PROMPT = """\
Analyze this image for use as a YouTube video thumbnail. Consider:
1. Readability of the episode number at small sizes
2. Visual appeal and click-worthiness
3. Consistency with a series of numbered episodes
4. Contrast and clarity on both light and dark backgrounds
Score 1-10 and explain your reasoning."""


def _load_api_key():
    """Load Gemini API key from ~/.config/.env."""
    env_path = Path(os.path.expanduser("~/.config/.env"))
    if not env_path.exists():
        raise SystemExit("~/.config/.env not found")
    for line in env_path.read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GEMINI_API_KEY not found in ~/.config/.env")


def _extract_score(text):
    """Extract a score N from 'N/10' pattern in text."""
    match = re.search(r"(\d+)\s*/\s*10", text)
    if match:
        return int(match.group(1))
    return 0


def generate_thumbnail(episode, candidates=3):
    """Generate thumbnail candidates, score them, and save the best one."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    key = _load_api_key()
    client = genai.Client(api_key=key)

    prompt = GENERATION_PROMPT.format(episode=episode)
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(aspect_ratio="16:9", image_size="1K"),
    )

    results = []

    for i in range(1, candidates + 1):
        print(f"Generating candidate {i}/{candidates}...")

        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=prompt,
            config=config,
        )

        # Extract image data from response parts
        image_data = None
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_data = part.inline_data
                break

        if not image_data:
            print(f"  WARNING: No image in candidate {i}, skipping.")
            continue

        # Save raw PNG
        raw_path = OUTPUT_DIR / f"thumb_{episode}_{i}.png"
        raw_path.write_bytes(image_data.data)
        print(f"  Saved {raw_path}")

        # Analyze with text model
        print(f"  Analyzing candidate {i}...")
        analysis = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(
                            data=image_data.data,
                            mime_type=image_data.mime_type,
                        ),
                        types.Part.from_text(ANALYSIS_PROMPT),
                    ]
                )
            ],
        )

        analysis_text = analysis.text or ""
        score = _extract_score(analysis_text)
        # Grab first line of reasoning as summary
        summary = analysis_text.strip().split("\n")[0][:120] if analysis_text else ""
        print(f"  Score: {score}/10 - {summary}")

        results.append((score, raw_path, i))

    if not results:
        raise SystemExit("No thumbnails were generated successfully.")

    # Pick best candidate
    results.sort(key=lambda r: r[0], reverse=True)
    best_score, best_path, best_idx = results[0]
    print(f"\nBest candidate: #{best_idx} (score {best_score}/10)")

    # Post-process with ImageMagick
    final_path = OUTPUT_DIR / f"folk-sequence-{episode}.jpg"
    print(f"Post-processing with ImageMagick...")

    subprocess.run(
        ["magick", str(best_path), "-resize", "1280x720!", "-quality", "95", str(final_path)],
        check=True,
    )

    print(f"Saved final thumbnail: {final_path}")
    print(f"\nSummary:")
    print(f"  Episode:    {episode}")
    print(f"  Candidates: {candidates} generated, {len(results)} scored")
    print(f"  Best score: {best_score}/10 (candidate #{best_idx})")
    print(f"  Output:     {final_path}")
