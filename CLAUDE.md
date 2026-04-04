# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The app runs on `http://127.0.0.1:5000`.

## Architecture

Single-file Flask app (`app.py`) with one HTML template (`templates/index.html`).

**Data flow:**
1. A background daemon thread (`start_background_refresh`) fetches forecast JSON from the BOM API on startup (if stale) and every 24 hours, writing atomically to `forecast.json` via a `.tmp` swap.
2. The frontend calls `/api/forecast` (GET) to read the cached file, or `/api/refresh` (POST) to trigger an immediate fetch.
3. `templates/index.html` is a self-contained page — it fetches `/api/forecast` on load, builds weather cards using DOM APIs, and references SVG `<symbol>` icons defined inline in the HTML.

**Key constants in `app.py`:**
- `BOM_API_URL` — the BOM daily forecast endpoint (hardcoded to location `r1qcmpg` = Fraser Rise, VIC)
- `FORECAST_FILE` — path to `forecast.json` alongside `app.py`
- `REFRESH_INTERVAL_HOURS` — cache TTL (default 24h)

**Weather icon mapping** (`templates/index.html`): `icon_descriptor` values from the BOM API (`sunny`, `mostly_sunny`, `shower`, `rain`, `thunderstorm`, `cloudy`, etc.) map to SVG `<symbol>` ids (`icon-sunny`, `icon-partly-sunny`, `icon-rain`, `icon-storm`, `icon-cloudy`).
<img width="3840" height="2076" alt="Screenshot 2026-04-04 at 13-52-43 Fraser Rise Weather" src="https://github.com/user-attachments/assets/865ed5a9-e19c-4d88-8670-634bfbba6176" />
