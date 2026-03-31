"""Verify all required tools and credentials are available."""

import shutil
import os
from pathlib import Path


def check_all():
    """Run all checks and report status."""
    ok = True

    # System tools
    tools = {
        "ffmpeg": "brew install ffmpeg",
        "ffprobe": "brew install ffmpeg",
        "magick": "brew install imagemagick",
    }
    print("System tools:")
    for tool, install in tools.items():
        path = shutil.which(tool)
        if path:
            print(f"  {tool}: {path}")
        else:
            print(f"  {tool}: MISSING ({install})")
            ok = False

    # Python packages
    print("\nPython packages:")
    packages = [
        ("googleapiclient", "google-api-python-client"),
        ("google_auth_oauthlib", "google-auth-oauthlib"),
        ("google.genai", "google-genai"),
    ]
    for module, package in packages:
        try:
            __import__(module)
            print(f"  {package}: OK")
        except ImportError:
            print(f"  {package}: MISSING (uv add {package})")
            ok = False

    # Gemini API key
    print("\nCredentials:")
    env_path = Path(os.path.expanduser("~/.config/.env"))
    if env_path.exists():
        content = env_path.read_text()
        if "GEMINI_API_KEY=" in content:
            print("  Gemini API key: OK")
        else:
            print("  Gemini API key: MISSING in ~/.config/.env")
            ok = False
    else:
        print("  ~/.config/.env: MISSING")
        ok = False

    # YouTube OAuth
    token_path = Path("token.json")
    secrets_path = Path("client_secrets.json")
    if token_path.exists():
        print("  YouTube token: OK")
    elif secrets_path.exists():
        print("  YouTube token: MISSING (run: uv run folkseq auth)")
        ok = False
    else:
        print("  YouTube OAuth: NOT CONFIGURED (need client_secrets.json)")
        ok = False

    # Output dirs
    print("\nOutput directories:")
    for d in ["output/channel", "output/thumbnails", "output/logs"]:
        p = Path(d)
        if p.exists():
            print(f"  {d}: OK")
        else:
            print(f"  {d}: will be created on first use")

    print()
    if ok:
        print("All checks passed.")
    else:
        print("Some checks failed. See above for details.")
