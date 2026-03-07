import time
import httpx
from logger import print_jikan
from rapidfuzz import fuzz, process
from config import FUZZY_MATCH_SCORE_CUTOFF, JIKAN_BASE_URL, JIKAN_REQUEST_DELAY_SECONDS

_anime_title_to_mal_id_cache: dict[str, int | None] = {}

_JIKAN_SEARCH_RESULT_LIMIT = 10
_JIKAN_MAX_RETRY_ATTEMPTS = 5
_JIKAN_RETRY_BASE_DELAY_SEC = 3.0
_JIKAN_REQUEST_TIMEOUT_SEC = 20


def _jikan_search(anime_title_query: str) -> list[dict]:
    retry_delay_seconds = _JIKAN_RETRY_BASE_DELAY_SEC
    for retry_attempt_number in range(_JIKAN_MAX_RETRY_ATTEMPTS):
        try:
            jikan_search_response = httpx.get(
                f"{JIKAN_BASE_URL}/anime",
                params={"q": anime_title_query, "limit": _JIKAN_SEARCH_RESULT_LIMIT, "sfw": False},
                timeout=_JIKAN_REQUEST_TIMEOUT_SEC,
            )
        except (httpx.TimeoutException, httpx.NetworkError) as network_error:
            if retry_attempt_number < _JIKAN_MAX_RETRY_ATTEMPTS - 1:
                print_jikan(f"Timeout for '{anime_title_query}', retrying in {retry_delay_seconds:.0f}s… ({network_error})")
                time.sleep(retry_delay_seconds)
                retry_delay_seconds = min(retry_delay_seconds * 2, 30)
            else:
                print_jikan(f"Gave up on '{anime_title_query}' after {_JIKAN_MAX_RETRY_ATTEMPTS} attempts")
            continue
        except Exception as unexpected_error:
            print_jikan(f"Unexpected error for '{anime_title_query}': {unexpected_error}")
            return []

        if jikan_search_response.status_code == 429:
            print_jikan(f"Rate-limited for '{anime_title_query}', waiting {retry_delay_seconds:.0f}s…")
            time.sleep(retry_delay_seconds)
            retry_delay_seconds = min(retry_delay_seconds * 2, 30)
            continue

        if jikan_search_response.status_code != 200:
            print_jikan(f"HTTP {jikan_search_response.status_code} for '{anime_title_query}'")
            return []

        return jikan_search_response.json().get("data", [])

    return []


def _extract_all_title_variants(jikan_anime_result: dict) -> list[str]:
    all_title_variants = [
        jikan_anime_result.get("title", ""),
        jikan_anime_result.get("title_english", "") or "",
        jikan_anime_result.get("title_japanese", "") or "",
    ]
    for title_entry in jikan_anime_result.get("titles", []):
        all_title_variants.append(title_entry.get("title", ""))
    return [title_variant.strip() for title_variant in all_title_variants if title_variant and title_variant.strip()]


def _try_fuzzy_match(anime_title_query: str, jikan_search_results: list[dict], minimum_score_cutoff: int) -> int | None:
    title_and_mal_id_pairs: list[tuple[str, int]] = []
    for jikan_anime_result in jikan_search_results:
        anime_mal_id = jikan_anime_result.get("mal_id")
        if not anime_mal_id:
            continue
        for title_variant in _extract_all_title_variants(jikan_anime_result):
            title_and_mal_id_pairs.append((title_variant, anime_mal_id))

    if not title_and_mal_id_pairs:
        return None

    all_candidate_titles = [title for title, _ in title_and_mal_id_pairs]
    for fuzzy_scorer in (fuzz.token_sort_ratio, fuzz.WRatio):
        best_fuzzy_match = process.extractOne(
            anime_title_query,
            all_candidate_titles,
            scorer=fuzzy_scorer,
            score_cutoff=minimum_score_cutoff,
        )
        if best_fuzzy_match:
            matched_title = best_fuzzy_match[0]
            return next(anime_mal_id for (title, anime_mal_id) in title_and_mal_id_pairs if title == matched_title)
    return None


def find_mal_id_for_title(anime_title: str) -> int | None:
    if anime_title in _anime_title_to_mal_id_cache:
        return _anime_title_to_mal_id_cache[anime_title]

    time.sleep(JIKAN_REQUEST_DELAY_SECONDS)

    original_title_search_results = _jikan_search(anime_title)
    if original_title_search_results:
        matched_mal_id = _try_fuzzy_match(anime_title, original_title_search_results, FUZZY_MATCH_SCORE_CUTOFF)
        if matched_mal_id:
            _anime_title_to_mal_id_cache[anime_title] = matched_mal_id
            return matched_mal_id

    title_cased_search_results: list[dict] = []
    title_case_variant = anime_title.title()
    if title_case_variant != anime_title:
        time.sleep(JIKAN_REQUEST_DELAY_SECONDS)
        title_cased_search_results = _jikan_search(title_case_variant)
        if title_cased_search_results:
            matched_mal_id = _try_fuzzy_match(anime_title, title_cased_search_results, FUZZY_MATCH_SCORE_CUTOFF)
            if matched_mal_id:
                _anime_title_to_mal_id_cache[anime_title] = matched_mal_id
                return matched_mal_id
            deduplicated_search_results = {
                r["mal_id"]: r for r in original_title_search_results + title_cased_search_results if "mal_id" in r
            }
            matched_mal_id = _try_fuzzy_match(anime_title, list(deduplicated_search_results.values()), FUZZY_MATCH_SCORE_CUTOFF)
            if matched_mal_id:
                _anime_title_to_mal_id_cache[anime_title] = matched_mal_id
                return matched_mal_id

    relaxed_fuzzy_score_cutoff = max(FUZZY_MATCH_SCORE_CUTOFF - 15, 50)
    all_combined_search_results = {
        r["mal_id"]: r for r in original_title_search_results + title_cased_search_results if "mal_id" in r
    }
    if all_combined_search_results:
        matched_mal_id = _try_fuzzy_match(anime_title, list(all_combined_search_results.values()), relaxed_fuzzy_score_cutoff)
        if matched_mal_id:
            print_jikan(f"Soft match (score ≥{relaxed_fuzzy_score_cutoff}) for '{anime_title}'")
            _anime_title_to_mal_id_cache[anime_title] = matched_mal_id
            return matched_mal_id

    _anime_title_to_mal_id_cache[anime_title] = None
    return None
