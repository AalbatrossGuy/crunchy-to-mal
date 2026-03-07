import httpx
from config import MAL_API_BASE_URL


def update_anime_list_entry(
    access_token: str,
    mal_anime_id: int,
    watch_status: str,
    episodes_watched: int | None = None,
) -> bool:
    mal_authorization_headers = {"Authorization": f"Bearer {access_token}"}
    mal_update_payload: dict = {"status": watch_status}

    if episodes_watched is not None:
        mal_update_payload["num_watched_episodes"] = episodes_watched

    mal_patch_response = httpx.patch(
        f"{MAL_API_BASE_URL}/anime/{mal_anime_id}/my_list_status",
        headers=mal_authorization_headers,
        data=mal_update_payload,
        timeout=10,
    )

    return mal_patch_response.status_code in (200, 201)
