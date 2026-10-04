# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WordPuzzle is a Flask vocabulary-learning app. Learners pick a level (primary: 30 weeks, secondary: 20 weeks), study a themed word list each week, and take a one-shot randomized spelling test. Results are tracked per word, and admins get a dashboard of progress across users and weeks.

GitHub remote: https://github.com/ashishsinghal2426/WordPuzzleNew

## Current Repo State

`words_data.py` is a **sample** set (primary weeks 1–3, secondary weeks 1–2, 5 words each); the remaining weeks show as "Coming soon" until the full lists are added. The templates and `static/css/style.css` were rebuilt to match the context each route passes; the originals were lost.

## Running the App

On this machine `python` (Microsoft Store) and `pip` (miniconda) are different interpreters, so use the project venv:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python main.py
```

The app runs on `http://localhost:5000` in debug mode. Flask-SQLAlchemy creates the SQLite database at `instance/wordpuzzle.db` (gitignored) on first run, and the word data is seeded from `words_data.py`.

Default admin credentials: `admin` / `admin123`

## Architecture

This is a Flask web application for a vocabulary learning game organized around weekly word sets.

**Entry point:** `main.py` — contains the Flask app, all routes, and a `init_db()` function that seeds words and creates the default admin on startup.

**Models (`models.py`):**
- `User` — authenticated users with a `level` field (`'primary'` or `'secondary'`) and `is_admin` flag
- `Word` — vocabulary words belonging to a `week_number` and `level`; `synonyms`/`antonyms` stored as JSON strings
- `TestAttempt` — one record per user per week per level (tests are one-shot; retaking is blocked)
- `TestAnswer` — per-word answer records linked to a `TestAttempt`, including `attempt_count` for how many tries the user needed

**Word data (`words_data.py`):** Exports `PRIMARY_WORDS` and `SECONDARY_WORDS` — lists of dicts with shape `{'week': int, 'theme': str, 'words': [...]}`. Each word is `{'word': str, 'meaning': str, 'pos'?: str, 'sentence'?: str, 'synonyms'?: [str], 'antonyms'?: [str]}` (see `init_db()` in `main.py`). Seeding only runs when the `Word` table is empty, so delete `instance/wordpuzzle.db` to reload changed word data. Primary level has 30 weeks; secondary has 20.

**Templates:** All extend `base.html` (navbar + flash messages). Route templates: `login.html`, `register.html`, `select_level.html`, `plan.html`, `week.html`, `test.html`, `results.html`, `admin.html`. `test.html` runs the test client-side (3 tries per word) and POSTs `{answers: [{word_id, user_answer, attempt_count}]}` to the submit endpoint.

**Key route flow:**
- `/` redirects to `/plan` (authenticated) or `/login`
- `/plan` — weekly progress overview
- `/week/<n>` — word list and study view for a week
- `/week/<n>/test` — randomized spelling test (one attempt per week)
- `/week/<n>/test/submit` — JSON POST endpoint; returns score and redirect URL
- `/week/<n>/results` — score breakdown
- `/api/word/<word>` — proxies to `dictionaryapi.dev`
- `/admin` — admin-only dashboard with per-user and per-week stats
