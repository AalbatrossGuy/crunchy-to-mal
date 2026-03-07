from rich import box
from rich.theme import Theme
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn


terminal = Console(theme=Theme({
    "success": "bold green",
    "failure": "bold red",
    "warning": "bold yellow",
    "info": "bold cyan",
    "muted": "dim white",
    "highlight": "bold magenta",
    "cr_cred": "bold orange1",
    "watching": "bold blue",
    "completed": "bold green",
    "plan_to_watch": "bold yellow",
}))


def print_banner():
    terminal.print(Panel.fit(
        "[bold magenta]Crunchyroll[/] [white]→[/] [bold blue]MyAnimeList[/]\n"
            "[muted]Sync your watchlist & crunchylists from Crunchyroll to MyAnimeList\nMade by AG(https://github.com/AalbatrossGuy)[/]",
        border_style="bright_magenta",
        padding=(1, 4),
    ))


def print_section(section_title: str):
    terminal.rule(f"[info]{section_title}[/]", style="bright_cyan")


def print_success(message: str):
    terminal.print(f"  [success]✓[/] {message}")


def print_failure(message: str):
    terminal.print(f"  [failure]✗[/] {message}")


def print_warning(message: str):
    terminal.print(f"  [warning]⚠[/] {message}")


def print_info(message: str):
    terminal.print(f"  [info]→[/] {message}")


def print_sync_row(anime_title: str, mal_watch_status: str, mal_anime_id: int):
    watch_status_rich_style = {
        "watching": "watching",
        "completed": "completed",
        "plan_to_watch": "plan_to_watch",
    }.get(mal_watch_status, "muted")

    status_display_label = mal_watch_status.replace("_", " ").upper()
    terminal.print(
        f"  [success]✓[/] [[{watch_status_rich_style}]{status_display_label:>13}[/]]  "
        f"[white]{anime_title}[/]  [muted](MAL #{mal_anime_id})[/]"
    )


def print_cr_credentials(display_email: str, masked_password: str, token_endpoint_url: str):
    terminal.print("  [cr_cred]┌─ Crunchyroll Credentials ────────────────────────────────────[/]")
    terminal.print(f"  [cr_cred]│[/]  CR_EMAIL    : [white]{display_email}[/]")
    terminal.print(f"  [cr_cred]│[/]  CR_PASSWORD : [white]{masked_password}[/]")
    terminal.print(f"  [cr_cred]│[/]  Token URL   : [white]{token_endpoint_url}[/]")
    terminal.print("  [cr_cred]└──────────────────────────────────────────────────────────────[/]")


def print_cr_warning(warning_message: str):
    terminal.print(f"  [warning]⚠[/] [cr_cred]{warning_message}[/]")


def print_jikan(jikan_log_message: str):
    terminal.print(f"  [bold magenta][Jikan][/] [magenta]{jikan_log_message}[/]")


def print_not_found(unmatched_anime_title: str):
    terminal.print(f"  [failure]✗[/] [muted]No MAL match found for:[/] [white]{unmatched_anime_title}[/]")


def print_summary(synced_count: int, not_found_count: int, failed_count: int):
    sync_summary_table = Table(box=box.ROUNDED, border_style="bright_magenta", show_header=False, padding=(0, 2))
    sync_summary_table.add_column(justify="right", style="muted")
    sync_summary_table.add_column(justify="left")

    sync_summary_table.add_row("Synced to MAL", f"[success]{synced_count}[/]")
    sync_summary_table.add_row("No match found", f"[warning]{not_found_count}[/]")
    sync_summary_table.add_row("API failures", f"[failure]{failed_count}[/]")

    terminal.print()
    terminal.print(Panel(sync_summary_table, title="[bold]Sync Complete[/]", border_style="bright_magenta"))
    terminal.print(
        "\n  [muted]View your updated list →[/] "
        "[link=https://myanimelist.net/animelist]https://myanimelist.net/animelist[/link]\n"
    )


def make_progress_bar() -> Progress:
    return Progress(
        SpinnerColumn(style="bright_magenta"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30, style="bright_magenta", complete_style="green"),
        TaskProgressColumn(),
        console=terminal,
        transient=False,
    )
