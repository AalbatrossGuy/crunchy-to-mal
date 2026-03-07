import json
import time
import httpx
import secrets
import webbrowser
import urllib.parse
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
from config import MAL_CLIENT_ID, MAL_OAUTH_BASE_URL, MAL_REDIRECT_URI, OAUTH_CALLBACK_TIMEOUT_SECONDS, TOKEN_CACHE_PATH, MAL_CLIENT_SECRET

_oauth_browser_callback_result: dict = {}

def _generate_pkce_pair() -> tuple[str, str]:
    pkce_code_verifier = secrets.token_urlsafe(64)
    pkce_code_challenge = pkce_code_verifier
    return pkce_code_verifier, pkce_code_challenge


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        oauth_callback_query_params = urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query
        )
        _oauth_browser_callback_result["code"] = oauth_callback_query_params.get("code",  [None])[0]
        _oauth_browser_callback_result["state"] = oauth_callback_query_params.get("state", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>Authorised! You can close this tab and return to your terminal.</h2>")

    def log_message(self, *_):
        pass


def _start_local_callback_server(oauth_callback_port: int) -> HTTPServer:
    local_callback_server = HTTPServer(("localhost", oauth_callback_port), _OAuthCallbackHandler)
    Thread(target=local_callback_server.handle_request, daemon=True).start()
    return local_callback_server


def _exchange_code_for_token(authorization_code: str, pkce_code_verifier: str) -> dict:
    token_exchange_payload = {
        "client_id": MAL_CLIENT_ID,
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": MAL_REDIRECT_URI,
        "code_verifier": pkce_code_verifier,
    }
    if MAL_CLIENT_SECRET:
        token_exchange_payload["client_secret"] = MAL_CLIENT_SECRET

    token_exchange_response = httpx.post(f"{MAL_OAUTH_BASE_URL}/token", data=token_exchange_payload)
    token_exchange_response.raise_for_status()

    access_token_data = token_exchange_response.json()
    access_token_data["expires_at"] = time.time() + access_token_data.get("expires_in", 3600)
    TOKEN_CACHE_PATH.write_text(json.dumps(access_token_data, indent=2))
    return access_token_data


def _refresh_access_token(existing_refresh_token: str) -> dict | None:
    token_refresh_payload = {
        "client_id": MAL_CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": existing_refresh_token,
    }
    if MAL_CLIENT_SECRET:
        token_refresh_payload["client_secret"] = MAL_CLIENT_SECRET

    try:
        token_refresh_response = httpx.post(f"{MAL_OAUTH_BASE_URL}/token", data=token_refresh_payload)
        token_refresh_response.raise_for_status()
        refreshed_token_data = token_refresh_response.json()
        refreshed_token_data["expires_at"] = time.time() + refreshed_token_data.get("expires_in", 3600)
        TOKEN_CACHE_PATH.write_text(json.dumps(refreshed_token_data, indent=2))
        return refreshed_token_data
    except Exception:
        return None


def get_mal_access_token() -> dict:
    if TOKEN_CACHE_PATH.exists():
        cached_token_data = json.loads(TOKEN_CACHE_PATH.read_text())

        if cached_token_data.get("expires_at", 0) > time.time() + 60:
            return cached_token_data

        if cached_token_data.get("refresh_token"):
            refreshed_token_data = _refresh_access_token(cached_token_data["refresh_token"])
            if refreshed_token_data:
                return refreshed_token_data

    pkce_code_verifier, pkce_code_challenge = _generate_pkce_pair()
    oauth_csrf_state = secrets.token_urlsafe(16)
    oauth_callback_port = int(urllib.parse.urlparse(MAL_REDIRECT_URI).port or 8765)

    mal_authorization_url = (
        f"{MAL_OAUTH_BASE_URL}/authorize"
        f"?response_type=code"
        f"&client_id={MAL_CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(MAL_REDIRECT_URI)}"
        f"&code_challenge={pkce_code_challenge}"
        f"&code_challenge_method=plain"
        f"&state={oauth_csrf_state}"
    )

    _start_local_callback_server(oauth_callback_port)
    webbrowser.open(mal_authorization_url)

    for _ in range(OAUTH_CALLBACK_TIMEOUT_SECONDS):
        if _oauth_browser_callback_result.get("code"):
            break
        time.sleep(1)
    else:
        raise TimeoutError("MAL OAuth2 browser authorisation timed out after 120 seconds.")

    return _exchange_code_for_token(_oauth_browser_callback_result["code"], pkce_code_verifier)
