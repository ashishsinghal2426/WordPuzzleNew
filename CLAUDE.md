# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
pip install -r requirements.txt
python main.py
```

The app runs on `http://localhost:5000` in debug mode. The SQLite database (`wordpuzzle.db`) and tables are created automatically on first run, and the word data is seeded from `words_data.py`.

Default admin credentials: `admin` / `admin123`

## Architecture

This is a Flask web application for a vocabulary learning game organized around weekly word sets.

**Entry point:** `main.py` — contains the Flask app, all routes, and a `init_db()` function that seeds words and creates the default admin on startup.

**Models (`models.py`):**
- `User` — authenticated users with a `level` field (`'primary'` or `'secondary'`) and `is_admin` flag
- `Word` — vocabulary words belonging to a `week_number` and `level`; `synonyms`/`antonyms` stored as JSON strings
- `TestAttempt` — one record per user per week per level (tests are one-shot; retaking is blocked)
- `TestAnswer` — per-word answer records linked to a `TestAttempt`, including `attempt_count` for how many tries the user needed

**Word data (`words_data.py`, not committed):** Exports `PRIMARY_WORDS` and `SECONDARY_WORDS` — lists of dicts with shape `{'week': int, 'theme': str, 'words': [...]}`. Primary level has 30 weeks; secondary has 20.

**Templates:** Jinja2 templates referenced by routes: `login.html`, `register.html`, `select_level.html`, `plan.html`, `week.html`, `test.html`, `results.html`, `admin.html`.

**Key route flow:**
- `/` redirects to `/plan` (authenticated) or `/login`
- `/plan` — weekly progress overview
- `/week/<n>` — word list and study view for a week
- `/week/<n>/test` — randomized spelling test (one attempt per week)
- `/week/<n>/test/submit` — JSON POST endpoint; returns score and redirect URL
- `/week/<n>/results` — score breakdown
- `/api/word/<word>` — proxies to `dictionaryapi.dev`
- `/admin` — admin-only dashboard with per-user and per-week stats
