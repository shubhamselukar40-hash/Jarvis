"""
Handles the one-time Google OAuth flow (Gmail + Calendar) and token storage.

Flow:
  1. You visit /auth/google on your deployed app (from your phone browser).
  2. You log in to Google and grant access.
  3. Google redirects back to /auth/google/callback, which saves a token file.
  4. From then on, gmail_service.py and calendar_service.py reuse that token
     (and silently refresh it) without you doing anything again.
"""
import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
]

TOKEN_PATH = os.environ.get("GOOGLE_TOKEN_PATH", "google_token.json")


def _client_config():
    return {
        "web": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.environ["GOOGLE_REDIRECT_URI"]],
        }
    }


def build_auth_url() -> str:
    flow = Flow.from_client_config(
        _client_config(), scopes=SCOPES, redirect_uri=os.environ["GOOGLE_REDIRECT_URI"]
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    return auth_url


def exchange_code_for_token(code: str):
    flow = Flow.from_client_config(
        _client_config(), scopes=SCOPES, redirect_uri=os.environ["GOOGLE_REDIRECT_URI"]
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())


def get_credentials() -> Credentials | None:
    """Returns valid credentials, refreshing if needed. None if not yet authorized."""
    if not os.path.exists(TOKEN_PATH):
        return None
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def is_authorized() -> bool:
    return get_credentials() is not None
