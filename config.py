import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CRUNCHYROLL_EMAIL = os.getenv("CR_EMAIL", "")
CRUNCHYROLL_PASSWORD = os.getenv("CR_PASSWORD", "")
MAL_CLIENT_ID = os.getenv("MAL_CLIENT_ID", "")
MAL_CLIENT_SECRET = os.getenv("MAL_CLIENT_SECRET", "")
MAL_REDIRECT_URI = os.getenv("MAL_REDIRECT_URI", "http://localhost:8765/callback")
TOKEN_CACHE_PATH = Path(".mal_token.json")


def _parse_bool(raw_env_value: str, fallback_default: bool) -> bool:
    if not raw_env_value:
        return fallback_default
    return raw_env_value.strip().lower() in ("1", "true", "yes")


SCRAPE_WATCHLIST = _parse_bool(os.getenv("SCRAPE_WATCHLIST", ""), True)
SCRAPE_HISTORY = _parse_bool(os.getenv("SCRAPE_HISTORY", ""), True)
SCRAPE_CRUNCHYLISTS = _parse_bool(os.getenv("SCRAPE_CRUNCHYLISTS", ""), True)

CRUNCHYROLL_STATUS_TO_MAL = {
    "watching": "watching",
    "completed": "completed",
    "plan_to_watch": "plan_to_watch",
}

JIKAN_BASE_URL = "https://api.jikan.moe/v4"
MAL_API_BASE_URL = "https://api.myanimelist.net/v2"
MAL_OAUTH_BASE_URL = "https://myanimelist.net/v1/oauth2"

JIKAN_REQUEST_DELAY_SECONDS = 0.4
MAL_REQUEST_DELAY_SECONDS = 0.3
FUZZY_MATCH_SCORE_CUTOFF = 70
OAUTH_CALLBACK_TIMEOUT_SECONDS = 120
PAGE_SCROLL_PAUSE_MS = 1200
MAX_PAGE_SCROLLS = 20


def validate_required_env_vars():
    missing_env_var_names = [
        env_var_name for env_var_name, env_var_value in {
            "CR_EMAIL": CRUNCHYROLL_EMAIL,
            "CR_PASSWORD": CRUNCHYROLL_PASSWORD,
            "MAL_CLIENT_ID": MAL_CLIENT_ID,
        }.items()
        if not env_var_value
    ]
    if missing_env_var_names:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_env_var_names)}\n"
            "Copy .env.example → .env and fill in your values."
        )
