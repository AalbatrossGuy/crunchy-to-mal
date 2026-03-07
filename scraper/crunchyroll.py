import time
import httpx
from dataclasses import dataclass
from logger import print_cr_credentials, print_cr_warning, print_info
from config import CRUNCHYROLL_EMAIL, CRUNCHYROLL_PASSWORD, SCRAPE_CRUNCHYLISTS, SCRAPE_HISTORY, SCRAPE_WATCHLIST

CR_BASE_URL = "https://www.crunchyroll.com"
CR_BETA_API = "https://beta-api.crunchyroll.com"
CR_TOKEN_URL = "https://www.crunchyroll.com/auth/v1/token"
CR_INDEX_PATH = "/index/v2"
CR_WATCHLIST_PATH = "/content/v1/{account_id}/watchlist"
CR_HISTORY_PATH = "/content/v2/{account_id}/watch-history"
CR_LISTS_PATH = "/content/v2/{account_id}/custom-lists"
CR_LIST_ITEMS_PATH = "/content/v2/{account_id}/custom-lists/{list_id}"
CR_BASIC_AUTH_HEADER = "Basic dC1rZGdwMmg4YzNqdWI4Zm4wZnE6eWZMRGZNZnJZdktYaDRKWFMxTEVJMmNDcXUxdjVXYW4="
CR_BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
CR_RESPONSE_LOCALE = "en-US"
CR_PAGINATION_PAGE_SIZE = 100
CR_API_RATE_LIMIT_DELAY = 0.3


def _print_credentials():
    display_email = CRUNCHYROLL_EMAIL or "(not set)"
    raw_password = CRUNCHYROLL_PASSWORD
    masked_password = ("*" * min(len(raw_password), 4) + "...") if len(raw_password) > 4 else "(not set)" if not raw_password else raw_password
    print_cr_credentials(display_email, masked_password, CR_TOKEN_URL)


@dataclass
class ScrapedAnimeEntry:
    title: str
    crunchyroll_status: str
    source_list_name: str = "watchlist"
    episodes_watched: int | None = None


@dataclass
class DiscoveredCrunchylist:
    name: str
    list_id: str
    item_count: int = 0


_cached_crunchyroll_auth: tuple[str, str] | None = None


def _login_with_credentials() -> tuple[str, str]:
    global _cached_crunchyroll_auth
    if _cached_crunchyroll_auth is not None:
        return _cached_crunchyroll_auth

    _print_credentials()

    crunchyroll_token_response = httpx.post(
        CR_TOKEN_URL,
        headers={
            "Authorization": CR_BASIC_AUTH_HEADER,
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": CR_BROWSER_USER_AGENT,
        },
        data={
            "grant_type": "password",
            "username": CRUNCHYROLL_EMAIL,
            "password": CRUNCHYROLL_PASSWORD,
            "scope": "offline_access",
        },
        timeout=15,
    )

    if crunchyroll_token_response.status_code == 401:
        raise RuntimeError(
            f"Crunchyroll login failed (401 Unauthorized).\n"
            f"  Email used : {CRUNCHYROLL_EMAIL or '(empty)'}\n"
            f"  Check that CR_EMAIL and CR_PASSWORD in your .env file are correct."
        )
    if crunchyroll_token_response.status_code == 403:
        raise RuntimeError(
            "Crunchyroll login blocked (403 Forbidden). "
            "Your IP may be rate-limited or Cloudflare is blocking the request. "
            "Try again in a few minutes."
        )
    crunchyroll_token_response.raise_for_status()
    crunchyroll_token_data = crunchyroll_token_response.json()
    crunchyroll_bearer_token = crunchyroll_token_data.get("access_token")

    if not crunchyroll_bearer_token:
        raise RuntimeError(
            f"Crunchyroll token response missing access_token. "
            f"Response: {crunchyroll_token_data}"
        )
    crunchyroll_account_id = crunchyroll_token_data.get("account_id")

    if not crunchyroll_account_id:
        crunchyroll_index_response = httpx.get(
            f"{CR_BETA_API}{CR_INDEX_PATH}",
            headers={
                "Authorization": f"Bearer {crunchyroll_bearer_token}",
                "User-Agent": CR_BROWSER_USER_AGENT,
            },
            timeout=15,
        )
        crunchyroll_index_response.raise_for_status()
        crunchyroll_account_id = crunchyroll_index_response.json().get("account_id")

    if not crunchyroll_account_id:
        raise RuntimeError("Could not determine Crunchyroll account ID.")

    _cached_crunchyroll_auth = (crunchyroll_bearer_token, crunchyroll_account_id)
    return _cached_crunchyroll_auth


def _authenticated_api_get(api_endpoint_url: str, crunchyroll_bearer_token: str, query_params: dict | None = None) -> dict:
    time.sleep(CR_API_RATE_LIMIT_DELAY)
    crunchyroll_api_response = httpx.get(
        api_endpoint_url,
        params=query_params or {},
        headers={
            "Authorization": f"Bearer {crunchyroll_bearer_token}",
            "User-Agent": CR_BROWSER_USER_AGENT,
        },
        timeout=15,
    )
    crunchyroll_api_response.raise_for_status()
    return crunchyroll_api_response.json()


def _fetch_all_pages(api_endpoint_url: str, crunchyroll_bearer_token: str, extra_query_params: dict | None = None) -> list[dict]:
    all_fetched_items: list[dict] = []
    pagination_start_offset: int = 0

    while True:
        request_params = {
            "locale": CR_RESPONSE_LOCALE,
            "n": CR_PAGINATION_PAGE_SIZE,
            "start":  pagination_start_offset,
        }
        if extra_query_params:
            request_params.update(extra_query_params)
        api_page_response = _authenticated_api_get(api_endpoint_url, crunchyroll_bearer_token, request_params)
        page_items = api_page_response.get("items") or api_page_response.get("data") or []
        all_fetched_items.extend(page_items)
        reported_total_count = api_page_response.get("total", 0)
        pagination_start_offset += len(page_items)
        if not page_items or (reported_total_count > 0 and pagination_start_offset >= reported_total_count):
            break

    return all_fetched_items


def _extract_series_title(raw_api_item: dict) -> str | None:
    content_panel = raw_api_item.get("panel", raw_api_item)
    content_panel_type = content_panel.get("type", "")
    if content_panel_type == "episode":
        episode_metadata = content_panel.get("episode_metadata", {})
        return episode_metadata.get("series_title") or content_panel.get("title")

    if content_panel_type == "":
        top_level_series_title = raw_api_item.get("series_title") or raw_api_item.get("title")
        if top_level_series_title:
            return top_level_series_title
        episode_metadata = content_panel.get("episode_metadata", {})
        if episode_metadata.get("series_title"):
            return episode_metadata["series_title"]

    return content_panel.get("title") or content_panel.get("slug_title")


def _scrape_watchlist(crunchyroll_bearer_token: str, crunchyroll_account_id: str) -> list[ScrapedAnimeEntry]:
    watchlist_api_url = f"{CR_BETA_API}{CR_WATCHLIST_PATH.format(account_id=crunchyroll_account_id)}"
    raw_watchlist_items = _fetch_all_pages(watchlist_api_url, crunchyroll_bearer_token)
    print_info(f"Watchlist: [white]{len(raw_watchlist_items)}[/] items fetched")
    scraped_entries: list[ScrapedAnimeEntry] = []
    seen_series_titles: set[str] = set()

    for raw_watchlist_item in raw_watchlist_items:
        series_title = _extract_series_title(raw_watchlist_item)
        if not series_title or series_title.lower() in seen_series_titles:
            continue
        seen_series_titles.add(series_title.lower())
        playhead_data = raw_watchlist_item.get("playhead")
        if isinstance(playhead_data, dict):
            is_fully_watched = playhead_data.get("fully_watched", False)
        else:
            is_fully_watched = False

        scraped_entries.append(ScrapedAnimeEntry(
            title=series_title,
            crunchyroll_status="completed" if is_fully_watched else "watching",
            source_list_name="My List",
        ))
    return scraped_entries


def _scrape_history(crunchyroll_bearer_token: str, crunchyroll_account_id: str) -> list[ScrapedAnimeEntry]:
    history_api_url = f"{CR_BETA_API}{CR_HISTORY_PATH.format(account_id=crunchyroll_account_id)}"
    raw_history_items = _fetch_all_pages(history_api_url, crunchyroll_bearer_token)
    print_info(f"History: [white]{len(raw_history_items)}[/] items fetched")

    scraped_entries: list[ScrapedAnimeEntry] = []
    seen_series_titles: set[str] = set()

    for raw_history_item in raw_history_items:
        series_title = _extract_series_title(raw_history_item)
        if not series_title or series_title.lower() in seen_series_titles:
            continue
        seen_series_titles.add(series_title.lower())
        scraped_entries.append(ScrapedAnimeEntry(
            title=series_title,
            crunchyroll_status="completed",
            source_list_name="Watch History",
        ))
    return scraped_entries


def discover_crunchylists(crunchyroll_bearer_token: str, crunchyroll_account_id: str) -> list[DiscoveredCrunchylist]:
    custom_lists_api_url = f"{CR_BETA_API}{CR_LISTS_PATH.format(account_id=crunchyroll_account_id)}"
    custom_lists_response = _authenticated_api_get(custom_lists_api_url, crunchyroll_bearer_token, {"locale": CR_RESPONSE_LOCALE})
    raw_crunchylists = custom_lists_response.get("items") or custom_lists_response.get("data") or []

    discovered_crunchylists = []
    for raw_list_entry in raw_crunchylists:
        list_display_name = raw_list_entry.get("title") or raw_list_entry.get("name") or raw_list_entry.get("list_title") or "(unnamed)"
        crunchylist_id = raw_list_entry.get("list_id") or raw_list_entry.get("id") or ""
        crunchylist_item_count = raw_list_entry.get("total") or raw_list_entry.get("item_count") or raw_list_entry.get("count") or 0
        if not crunchylist_id:
            print_cr_warning(f"Crunchylist entry missing list_id, skipping: {raw_list_entry}")
            continue
        discovered_crunchylists.append(DiscoveredCrunchylist(
            name=list_display_name,
            list_id=crunchylist_id,
            item_count=crunchylist_item_count,
        ))

    return discovered_crunchylists


def _scrape_crunchylist(
    crunchyroll_bearer_token: str,
    crunchyroll_account_id: str,
    crunchylist: DiscoveredCrunchylist,
    assigned_mal_status: str,
) -> list[ScrapedAnimeEntry]:
    crunchylist_items_api_url = f"{CR_BETA_API}{CR_LIST_ITEMS_PATH.format(account_id=crunchyroll_account_id, list_id=crunchylist.list_id)}"
    raw_crunchylist_items = _fetch_all_pages(crunchylist_items_api_url, crunchyroll_bearer_token)

    scraped_entries: list[ScrapedAnimeEntry] = []
    seen_series_titles: set[str] = set()

    for raw_crunchylist_item in raw_crunchylist_items:
        series_title = _extract_series_title(raw_crunchylist_item)
        if not series_title or series_title.lower() in seen_series_titles:
            continue
        seen_series_titles.add(series_title.lower())
        scraped_entries.append(ScrapedAnimeEntry(
            title=series_title,
            crunchyroll_status=assigned_mal_status,
            source_list_name=crunchylist.name,
        ))
    return scraped_entries


def scrape_all_sources(
    crunchylist_to_mal_status_map: dict[str, str],
) -> tuple[list[ScrapedAnimeEntry], list[DiscoveredCrunchylist]]:
    crunchyroll_bearer_token, crunchyroll_account_id = _login_with_credentials()

    all_scraped_entries: list[ScrapedAnimeEntry] = []
    discovered_crunchylists: list[DiscoveredCrunchylist] = []

    if SCRAPE_WATCHLIST:
        all_scraped_entries.extend(_scrape_watchlist(crunchyroll_bearer_token, crunchyroll_account_id))

    if SCRAPE_HISTORY:
        already_seen_titles = {anime_entry.title.lower() for anime_entry in all_scraped_entries}
        all_scraped_entries.extend(
            anime_entry for anime_entry in _scrape_history(crunchyroll_bearer_token, crunchyroll_account_id)
            if anime_entry.title.lower() not in already_seen_titles
        )

    if SCRAPE_CRUNCHYLISTS:
        discovered_crunchylists = discover_crunchylists(crunchyroll_bearer_token, crunchyroll_account_id)
        for crunchylist in discovered_crunchylists:
            assigned_mal_status = crunchylist_to_mal_status_map.get(crunchylist.name, "plan_to_watch")
            already_seen_titles = {anime_entry.title.lower() for anime_entry in all_scraped_entries}
            all_scraped_entries.extend(
                anime_entry for anime_entry in _scrape_crunchylist(
                    crunchyroll_bearer_token, crunchyroll_account_id, crunchylist, assigned_mal_status
                )
                if anime_entry.title.lower() not in already_seen_titles
            )

    return all_scraped_entries, discovered_crunchylists
