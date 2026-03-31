"""Generate and set YouTube channel metadata and assets."""

import os
from pathlib import Path

from folkseq.auth import build_youtube

OUTPUT_DIR = Path("output/channel")

CHANNEL_DESCRIPTION = (
    "Screen recordings of music creation in Bitwig Studio. "
    "Each episode captures a full session building a new track from scratch. "
    "No narration, no edits \u2014 just the creative process.\n"
)

CHANNEL_KEYWORDS = (
    "bitwig studio music production screen recording daw "
    "electronic music folk ambient generative"
)


def set_channel_metadata(youtube=None):
    """Set channel description and keywords via YouTube API."""
    if youtube is None:
        youtube = build_youtube()

    # Get current channel info
    response = youtube.channels().list(part="id,brandingSettings", mine=True).execute()

    if not response.get("items"):
        print("ERROR: No channel found for authenticated account.")
        raise SystemExit(1)

    channel = response["items"][0]
    channel_id = channel["id"]
    print(f"Channel ID: {channel_id}")

    # Update branding settings
    channel["brandingSettings"]["channel"]["description"] = CHANNEL_DESCRIPTION
    channel["brandingSettings"]["channel"]["keywords"] = CHANNEL_KEYWORDS

    youtube.channels().update(
        part="brandingSettings",
        body=channel,
    ).execute()

    print("Updated channel description and keywords.")


def upload_banner(youtube=None):
    """Upload channel banner image via YouTube API."""
    from googleapiclient.http import MediaFileUpload

    if youtube is None:
        youtube = build_youtube()

    banner_path = OUTPUT_DIR / "banner.png"
    if not banner_path.exists():
        print(f"ERROR: Banner not found at {banner_path}")
        print("Run: uv run folkseq channel --type banner  (to generate first)")
        raise SystemExit(1)

    print(f"Uploading banner from {banner_path}...")

    # Step 1: Upload banner image
    media = MediaFileUpload(str(banner_path), mimetype="image/png")
    response = youtube.channelBanners().insert(media_body=media).execute()
    banner_url = response["url"]
    print(f"Banner uploaded. URL: {banner_url}")

    # Step 2: Set banner on channel
    channels_response = youtube.channels().list(
        part="id,brandingSettings", mine=True
    ).execute()
    channel = channels_response["items"][0]

    if "image" not in channel["brandingSettings"]:
        channel["brandingSettings"]["image"] = {}
    channel["brandingSettings"]["image"]["bannerExternalUrl"] = banner_url

    youtube.channels().update(
        part="brandingSettings",
        body=channel,
    ).execute()

    print("Channel banner set successfully.")


def generate_assets(asset_type="all"):
    """Generate channel assets with Gemini and/or set them on YouTube."""
    youtube = build_youtube()

    if asset_type in ("all", "metadata"):
        set_channel_metadata(youtube)

    if asset_type in ("all", "banner"):
        upload_banner(youtube)

    if asset_type == "profile":
        profile_path = OUTPUT_DIR / "profile.png"
        if profile_path.exists():
            print(f"\nProfile picture is at: {profile_path}")
            print("YouTube API cannot set profile pictures.")
            print("Upload manually at: https://myaccount.google.com/personal-info")
        else:
            print("ERROR: Profile picture not found. Generate it first.")

    if asset_type == "all":
        profile_path = OUTPUT_DIR / "profile.png"
        print(f"\nProfile picture: {profile_path}")
        print("(Must be uploaded manually at https://myaccount.google.com/personal-info)")

    print("\nDone.")
