# crunchyroll-to-mal

![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![License](https://img.shields.io/badge/license-MIT-green)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/9a3497045ade4781b462c827c9f20870)](https://app.codacy.com/gh/AalbatrossGuy/crunchy-to-mal/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
![Maintained](https://img.shields.io/badge/maintained-yes-green)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)

So, recently I realised that I had a [MyAnimeList](http://myanimelist.net/) account that was sitting dormant since 2022 with outdated lists that I no longer kept up-to-date. Since I primarily watch anime in [Crunchyroll](https://crunchyroll.com/) now, I saw my crunchylists and it had more than 200 entries. Bruh, Who's gonna manually add 200 entries to MAL. I don't have that much time. So I wrote this script to do that for me.

This script syncs your Crunchyroll watch history, my list & crunchylists to your [MyAnimeList](https://myanimelist.net) account.

---

## Screenshots

<img width="1918" height="1218" alt="main-shot-1" src="https://github.com/user-attachments/assets/29c8b5ad-ea94-4145-a561-f150bd8baaa2" /><br>

---
<img width="1372" height="276" alt="main-shot-2" src="https://github.com/user-attachments/assets/426e81b8-9eeb-4efe-8c7c-83881a7589d8" /><br>

---
<img width="1931" height="210" alt="main-shot-3" src="https://github.com/user-attachments/assets/5b61d696-a01f-4eb7-bc24-484826d69e21" />

---

## Features

- Syncs from your Crunchyroll `My List`, `Watch History`, and `Crunchylists` 
- Configure watch status for each crunchylist(s).
- Repeat entries get skipped.
- Color-coded terminal output with a live progress bar (cause why not).

---

## Requirements

- Python 3.11+
- A [MAL API client](https://myanimelist.net/apiconfig)
- A Crunchyroll account with a username/password login

---


## Dependencies

- `httpx`
- `rapidfuzz`
- `rich`
- `python-dotenv`
---

## Installation

```bash
git clone https://github.com/AalbatrossGuy/crunchy-to-mal
cd crunchy-to-mal
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

---

## Configuration

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

### Setting up a MAL API client

1. Go to [myanimelist.net/apiconfig](https://myanimelist.net/apiconfig) and click **Create ID**
2. Set **App Redirect URL** to `http://localhost:8765/callback`
3. Copy the **Client ID** into your `.env`

---

## Usage

```bash
python3 main.py
```

On first run, a browser window will open for MAL OAuth2 auth. After approving, the token is cached to `.mal_token.json` and reused on future runs. Token auto-refreshes when expired.

If Crunchylists are enabled, you'll be prompted to assign a MAL status to each list before syncing begins.

After syncing completes, you'll see a small summary window showing some statistics.

---

## Project structure

```
crunchyroll-to-mal/
├── main.py
├── config.py
├── logger.py
├── api/
│   └── mal_api.py
├── auth/
│   └── mal_auth.py
├── matcher/
│   └── jikan.py
└── scraper/
    └── crunchyroll.py
```
---

## Contribution
Pull Requests are welcome! However don't always expect fast response. I'll try my best to address the issue(s) as fast as possible.

---
 <br>

> Fair Disclaimer: This project is not shitty vibe coded except for the colorful terminal logs cause I've never done it before. Reference sources for this project - [1](https://github.com/hyugogirubato/API-Crunchyroll-Beta/wiki) - [2](https://github.com/Vryntel/Crunchyroll-Export-Import-List/blob/main/Code.gs) - [3](https://github.com/jbsky/crunchyroll-api/tree/main) - [4](https://github.com/DanielEstrada1/crunchyroll_webscraper) - [5](https://github.com/patmendoza330/crunchyrolltitles).
