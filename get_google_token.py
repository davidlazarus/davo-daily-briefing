"""
One-time script to generate Google OAuth2 refresh token.
Run this LOCALLY (not on Railway) — it opens a browser for you to log in.

Usage:
  1. Make sure credentials.json is in this directory
     (downloaded from Google Cloud Console → Credentials → OAuth Client ID)
  2. Run: python get_google_token.py
  3. Log in via the browser window that opens
  4. Copy the printed values into your .env file
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def main():
    # Load OAuth client config
    try:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    except FileNotFoundError:
        print("ERROR: credentials.json not found!")
        print("Download it from Google Cloud Console → APIs & Services → Credentials")
        print("(OAuth Client ID → Download JSON → rename to credentials.json)")
        return

    # Run local server to handle the OAuth callback
    creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")

    # Extract what we need
    print("\n" + "=" * 50)
    print("  SUCCESS! Add these to your .env file:")
    print("=" * 50)

    # Read client ID and secret from credentials.json
    with open("credentials.json") as f:
        client_config = json.load(f)
        installed = client_config.get("installed", client_config.get("web", {}))

    print(f"\nGOOGLE_CLIENT_ID={installed['client_id']}")
    print(f"GOOGLE_CLIENT_SECRET={installed['client_secret']}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
