import time
from api.mal_api import update_anime_list_entry
from auth.mal_auth import get_mal_access_token
from matcher.jikan import find_mal_id_for_title
from config import CRUNCHYROLL_STATUS_TO_MAL, MAL_REQUEST_DELAY_SECONDS
from scraper.crunchyroll import DiscoveredCrunchylist, scrape_all_sources
from logger import print_summary, print_sync_row, print_warning, terminal
from config import SCRAPE_CRUNCHYLISTS, SCRAPE_HISTORY, SCRAPE_WATCHLIST, validate_required_env_vars
from logger import make_progress_bar, print_banner, print_failure, print_info, print_not_found, print_section, print_success

MAL_STATUS_CHOICES = ["watching", "completed", "plan_to_watch", "on_hold", "dropped"]


def prompt_status_for_crunchylist(crunchylist: DiscoveredCrunchylist) -> str:
    terminal.print(
        f"\n  [bold white]{crunchylist.name}[/]  "
        f"[dim]({crunchylist.item_count} items)[/]"
    )
    for status_index, status_value in enumerate(MAL_STATUS_CHOICES, start=1):
        status_display_label = status_value.replace("_", " ").upper()
        terminal.print(f"    [dim]{status_index}.[/] [cyan]{status_display_label}[/]")

    while True:
        user_status_input = terminal.input("  [dim]→ Choose status (1–5):[/] ").strip()
        if user_status_input.isdigit() and 1 <= int(user_status_input) <= len(MAL_STATUS_CHOICES):
            chosen_mal_status = MAL_STATUS_CHOICES[int(user_status_input) - 1]
            print_success(
                f"[dim]{crunchylist.name}[/] → "
                f"[bold cyan]{chosen_mal_status.replace('_', ' ').upper()}[/]"
            )
            return chosen_mal_status
        print_warning("Enter a number between 1 and 5.")


def run_sync():
    print_banner()

    try:
        validate_required_env_vars()
    except EnvironmentError as missing_env_vars_error:
        print_failure(str(missing_env_vars_error))
        return

    active_source_names = [
        source_name for source_name, is_source_enabled in {
            "My List": SCRAPE_WATCHLIST,
            "Watch History": SCRAPE_HISTORY,
            "Crunchylists": SCRAPE_CRUNCHYLISTS,
        }.items() if is_source_enabled
    ]

    if not active_source_names:
        print_warning("Nothing to scrape. Set atleast one source to true.")
        return

    print_section("MAL Authentication")
    with terminal.status("[info]Authenticating with MyAnimeList…[/]", spinner="dots"):
        try:
            mal_oauth_token = get_mal_access_token()
            mal_access_token = mal_oauth_token["access_token"]
            print_success("MyAnimeList access token ready")
        except Exception as mal_auth_error:
            print_failure(f"MAL authentication failed: {mal_auth_error}")
            return

    print_section("Crunchyroll Authentication")
    print_info(f"Active sources: {', '.join(active_source_names)}")

    crunchylist_to_mal_status_map: dict[str, str] = {}

    if SCRAPE_CRUNCHYLISTS:
        with terminal.status("[info]Discovering Crunchylists…[/]", spinner="dots"):
            from scraper.crunchyroll import _login_with_credentials, discover_crunchylists
            crunchyroll_bearer_token, crunchyroll_account_id = _login_with_credentials()
            discovered_crunchylists = discover_crunchylists(crunchyroll_bearer_token, crunchyroll_account_id)

        if discovered_crunchylists:
            print_success(f"Found {len(discovered_crunchylists)} Crunchylist(s)")
            print_section("Assign List Status")
            for crunchylist in discovered_crunchylists:
                crunchylist_to_mal_status_map[crunchylist.name] = prompt_status_for_crunchylist(crunchylist)
        else:
            print_warning("No Crunchylists found — skipping.")

    print_section("Scraping All Sources")
    with terminal.status("[info]Logging in to Crunchyroll…[/]", spinner="dots"):
        try:
            all_scraped_entries, _ = scrape_all_sources(crunchylist_to_mal_status_map)
        except RuntimeError as crunchyroll_login_error:
            print_failure(str(crunchyroll_login_error))
            return

    entries_per_source: dict[str, int] = {}
    for anime_entry in all_scraped_entries:
        entries_per_source[anime_entry.source_list_name] = (
            entries_per_source.get(anime_entry.source_list_name, 0) + 1
        )

    print_success(f"Scraped [bold]{len(all_scraped_entries)}[/] total anime entries")
    for source_name, source_entry_count in entries_per_source.items():
        print_info(f"{source_entry_count} × from [white]{source_name}[/]")

    if not all_scraped_entries:
        print_warning("No anime entries found.")
        return

    print_section("Matching & Syncing to MAL")
    sync_result_counts = {"synced": 0, "not_found": 0, "failed": 0}
    sync_progress_bar = make_progress_bar()
    sync_progress_task = sync_progress_bar.add_task("[info]Syncing entries…[/]", total=len(all_scraped_entries))

    with sync_progress_bar:
        for anime_entry in all_scraped_entries:
            sync_progress_bar.update(
                sync_progress_task,
                description=f"[info]Matching:[/] [white]{anime_entry.title[:40]}[/]",
            )

            matched_mal_anime_id = find_mal_id_for_title(anime_entry.title)

            if matched_mal_anime_id is None:
                print_not_found(anime_entry.title)
                sync_result_counts["not_found"] += 1
                sync_progress_bar.advance(sync_progress_task)
                continue

            mapped_mal_watch_status = CRUNCHYROLL_STATUS_TO_MAL.get(
                anime_entry.crunchyroll_status,
                anime_entry.crunchyroll_status,
            )

            mal_update_succeeded = update_anime_list_entry(
                access_token=mal_access_token,
                mal_anime_id=matched_mal_anime_id,
                watch_status=mapped_mal_watch_status,
                episodes_watched=anime_entry.episodes_watched,
            )

            if mal_update_succeeded:
                print_sync_row(anime_entry.title, mapped_mal_watch_status, matched_mal_anime_id)
                sync_result_counts["synced"] += 1
            else:
                print_failure(f"MAL API update failed for: {anime_entry.title}")
                sync_result_counts["failed"] += 1

            sync_progress_bar.advance(sync_progress_task)
            time.sleep(MAL_REQUEST_DELAY_SECONDS)

    print_summary(synced_count=sync_result_counts["synced"], not_found_count=sync_result_counts["not_found"], failed_count=sync_result_counts["failed"],)


if __name__ == "__main__":
    run_sync()
