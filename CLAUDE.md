# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WordPuzzle is a Flask vocabulary-learning app. Learners pick a level (primary: 30 weeks, secondary: 20 weeks), study a themed word list each week, and take a randomized spelling test (up to 3 attempts per week). Results are tracked per word, and admins get a dashboard of progress across users and weeks.

GitHub remote: https://github.com/ashishsinghal2426/WordPuzzleNew

## Current Repo State

The full word lists are in (500 words: 10 per week across 30 primary and 20 secondary weeks). The templates and `static/css/style.css` were rebuilt to match the context each route passes; the originals were lost.

## Running the App

On this machine `python` (Microsoft Store) and `pip` (miniconda) are different interpreters, so use the project venv:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python main.py
```

The app runs on `http://localhost:5000` in debug mode. Flask-SQLAlchemy creates the SQLite database at `instance/wordpuzzle.db` (gitignored) on first run, and the word data is seeded from the `words_data/` package.

Default admin credentials: `admin` / `admin123`

## Architecture

This is a Flask web application for a vocabulary learning game organized around weekly word sets.

**Entry point:** `main.py` — contains the Flask app, all routes, and `setup_database()`, which runs on startup (see Startup).

**Models (`models.py`):**
- `User` — authenticated users with a `level` field (`'primary'` or `'secondary'`) and `is_admin` flag
- `Word` — vocabulary words belonging to a `week_number` and `level`; `synonyms`/`antonyms` stored as JSON strings
- `TestAttempt` — one record per sitting of a week's test, with `attempt_number` (1 to `MAX_ATTEMPTS`) and a unique constraint on (user, level, week, attempt_number). Tests are not one-shot: up to `MAX_ATTEMPTS = 3` attempts per user per level per week, and all are kept
- `TestAnswer` — per-word answer records linked to a `TestAttempt`, with `status` (`correct` / `incorrect` / `unattempted`, constants in `models.py`), `is_correct`, and `attempt_count` for how many tries the user needed (1 to 3, 0 when unattempted)

**Word data (`words_data/` package):** `primary.py` and `secondary.py` export `PRIMARY_WORDS` and `SECONDARY_WORDS` (re-exported by `__init__.py`) — lists of dicts with shape `{'week': int, 'theme': str, 'words': [...]}`. Each word is `{'word': str, 'meaning': str, 'pos': str, 'sentence': str, 'synonyms'?: [str], 'antonyms'?: [str]}`. Primary has 30 weeks, secondary 20, exactly 10 words each. `validation.py` has `validate_word_data()`, which returns a list of problems (week counts, 10 words per week, theme, required fields `word`/`pos`/`meaning`/`sentence`, letters-only words, sentence contains the word, no duplicate words within a level); `setup_database()` raises `WordDataError` if the list is non-empty.

**Startup (`setup_database()` in `main.py`),** in order:
1. Validate the word data; raise `WordDataError` on any problem (`__main__` prints them to stderr and exits 1).
2. One-time legacy upgrade: if `test_attempt` exists without the `attempt_number` column (the old one-shot schema), back up the SQLite file to `<db>.bak-<timestamp>`, then drop `test_answer` and `test_attempt`. Old test history is deliberately discarded. Once the new schema exists this never fires again.
3. `db.create_all()`.
4. `_add_missing_words()` — inserts any word not already present per (level, lowercase word); existing words and users are kept.
5. `_ensure_admin()` — creates the default admin if absent.

The database URI comes from the `WORDPUZZLE_DATABASE_URI` env var, defaulting to `sqlite:///wordpuzzle.db` (`instance/wordpuzzle.db`). The tests use it to point at a temporary database. Future schema changes need the same kind of detection (inspect the existing tables and upgrade explicitly), because `create_all()` never alters existing tables; or adopt Flask-Migrate.

**Templates:** All extend `base.html` (navbar + flash messages). Route templates: `login.html`, `register.html`, `select_level.html`, `plan.html`, `week.html`, `test.html`, `results.html`, `admin.html`. `test.html` runs the test client-side (3 tries per word, plus a Skip button) and POSTs `{attempt_number, answers: [{word_id, user_answer, attempt_count}]}` to the submit endpoint. Skipping a word with no tries yet sends an empty answer, stored as `unattempted` (`attempt_count` 0); skipping after a wrong try sends the last wrong answer, stored as `incorrect`. A word that never got a correct answer in 3 tries is `incorrect`.

**Key route flow:**
- `/` redirects to `/plan` (authenticated) or `/login`
- `/plan` — weekly progress overview, with attempts used and the latest score per week
- `/week/<n>` — word list and study view for a week
- `/week/<n>/test` — randomized spelling test (redirects to results once all 3 attempts are used)
- `/week/<n>/test/submit` — JSON POST endpoint; returns score and redirect URL; stale, duplicate or over-limit submits are ignored (no write)
- `/week/<n>/results` — score breakdown, with attempt history
- `/api/word/<word>` — proxies to `dictionaryapi.dev`
- `/admin` — admin-only dashboard with learner progress (weeks completed, attempts used), a table of every test with its score percentage, and per-week averages

## Testing

Run the pytest suite (pinned in `requirements.txt`):

```bash
.venv/Scripts/python -m pytest -q
```

`tests/conftest.py` sets `WORDPUZZLE_DATABASE_URI` to a temporary SQLite file before importing `main`, so tests never touch `instance/wordpuzzle.db`. Suites cover word data validation, `setup_database()` (including the legacy upgrade), attempts, and pages. The test page's inline JS in `test.html` is syntax-checked by `test_test_page_script_is_valid_js` in `tests/test_pages.py` (`node --check`, skipped if node is missing); the client-side flow itself (tries, Skip) is not exercised by pytest.

## Gotchas

- Debug mode starts a reloader child process. After stopping the server, confirm nothing is still listening on port 5000.
- `/api/word/<word>` depends on `api.dictionaryapi.dev`, which is sometimes down (Cloudflare 522). A 502 from the proxy usually means the upstream is unavailable, not an app bug.
- Week counts (`WEEKS_PER_LEVEL`) and words per week (`WORDS_PER_WEEK`) are constants in `main.py`; the validator checks the word data against them at startup.
- Answers are graded server-side (case-insensitive, trimmed) in `week_test_submit`; the client-side check in `test.html` only drives the 3-try UI. Edited word text is not updated in existing rows (`_add_missing_words()` only inserts), so change an existing word's fields in the database or delete `instance/wordpuzzle.db`.
- `app.secret_key` and the default admin password are hardcoded in `main.py`; change both before any deployment.

## Repo Conventions

- Commit messages follow `.claude/Commands/Commit-Message.md`: `<emoji> <type>: <description>` (`✨ feat`, `🐛 fix`, `🔨 refactor`, `📝 docs`, `🎨 style`, `✅ test`, `⚡ perf`), present tense, with a body explaining why. Propose the message and wait for approval before committing.
- `.claude/` also holds a `spec` command (templates in `.claude/_specs/`) and the `figma-design-extractor` agent. `.claude/settings.local.json` is personal and gitignored.
- `.venv/` and `instance/` (the SQLite database) are gitignored; never commit `*.db` files.
