"""YouTube OAuth 2.0 authentication flow."""

import json
import os
from pathlib import Path

TOKEN_PATH = Path("token.json")
CLIENT_SECRETS_PATH = Path("client_secrets.json")

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def get_credentials():
    """Load or refresh YouTube OAuth credentials."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())
        return creds

    if creds and creds.valid:
        return creds

    return None


def authenticate():
    """Run the OAuth 2.0 authorization flow (opens browser)."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CLIENT_SECRETS_PATH.exists():
        print("ERROR: client_secrets.json not found.")
        print()
        print("To set up YouTube API access:")
        print("  1. Go to https://console.cloud.google.com/apis/dashboard")
        print("  2. Create a project (or select existing)")
        print("  3. Enable 'YouTube Data API v3'")
        print("  4. Go to Credentials > Create Credentials > OAuth client ID")
        print("  5. Application type: Desktop app")
        print("  6. Download JSON and save as client_secrets.json in this directory")
        print()
        print("Then run: uv run folkseq auth")
        raise SystemExit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json())
    print(f"Authenticated successfully. Token saved to {TOKEN_PATH}")
    return creds


def build_youtube():
    """Build an authenticated YouTube API service client."""
    from googleapiclient.discovery import build

    creds = get_credentials()
    if not creds:
        print("Not authenticated. Run: uv run folkseq auth")
        raise SystemExit(1)

    return build("youtube", "v3", credentials=creds)
