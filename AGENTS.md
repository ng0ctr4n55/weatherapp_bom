# Repository Guidelines

## Project Structure & Module Organization
`app.py` is the only Python application entrypoint. It serves the HTML UI at `/` and the JSON endpoints under `/api/*`, and it also manages forecast refresh and cache writes to `forecast.json`. Frontend markup, styles, and browser-side logic live in `templates/index.html`. Deployment artifacts are at the repo root: `Dockerfile` for container builds and `weatherapp-bom.service` for running the container under `systemd`.

## Build, Test, and Development Commands
Create an isolated environment, install Flask, and run the app locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The app listens on `http://localhost:5000`. Build the container with `docker build -t weatherapp-bom .` and run it with `docker run --rm -p 5000:5000 weatherapp-bom`.

## Coding Style & Naming Conventions
Follow existing Python style in `app.py`: 4-space indentation, standard-library imports first, concise docstrings on non-trivial functions, and `snake_case` for functions and variables. Keep route handlers small and move shared logic into helpers such as `fetch_forecast()` or `is_cache_stale()`. In `templates/index.html`, preserve the current plain HTML/CSS/JavaScript structure and use clear IDs or class names like `refresh-btn` and `last-updated`.

## Testing Guidelines
There is no automated test suite in the repository yet. For backend changes, manually verify `GET /api/forecast`, `POST /api/refresh`, stale-cache behavior, and rendering at `/`. If you add tests, prefer `pytest`, place them under `tests/`, and name files `test_*.py`. Keep sample payloads small and deterministic.

## Commit & Pull Request Guidelines
Recent commits use short imperative summaries such as `refactor` and `improve app`; `CONTRIBUTING.md` also shows conventional-style examples like `feat: ...`. Prefer concise imperative commit messages and use a prefix such as `feat:`, `fix:`, or `docs:` when it adds clarity. PRs should describe the user-visible change, list manual verification steps, and include screenshots for UI edits in `templates/index.html`.

## Configuration & Data Notes
Do not hardcode new secrets or environment-specific paths. If you change refresh timing, cache behavior, or BOM API access, update both code comments and deployment files so local runs, Docker, and `systemd` stay aligned.
