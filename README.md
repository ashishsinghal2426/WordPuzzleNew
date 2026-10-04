# WordPuzzle

A Flask web app for building vocabulary through weekly word sets. Learners pick a level (**Primary**, 30 weeks, or **Secondary**, 20 weeks), study each week's themed word list with meanings, example sentences, synonyms and antonyms, then take a one-time randomized spelling test. Results are saved per word, and an admin dashboard shows progress across users and weeks.

## Features

- User registration and login, with a level chosen per learner
- Weekly plan showing progress across all weeks
- Study view per week, with live definitions from [dictionaryapi.dev](https://dictionaryapi.dev)
- Randomized spelling test, one attempt per week, with per-word attempt tracking
- Score breakdown after each test
- Admin dashboard with per-user and per-week stats

## Getting started

```bash
pip install -r requirements.txt
python main.py
```

Open http://localhost:5000. On first run the app creates the SQLite database (`instance/wordpuzzle.db`), loads the words from `words_data.py`, and creates a default admin account: `admin` / `admin123` (change it before deploying).

> **Note:** `words_data.py` currently holds a small sample set (a few weeks per level). Replace it with the full word lists; see [CLAUDE.md](CLAUDE.md) for the expected format.

## Tech stack

Flask · Flask-SQLAlchemy (SQLite) · Flask-Login · Jinja2 · requests

## Project structure

```
main.py           Flask app, routes, and database seeding
models.py         User, Word, TestAttempt, TestAnswer models
words_data.py     Weekly word lists (sample data)
templates/        Jinja2 page templates
static/           CSS and JavaScript
```

## License

MIT. See [LICENSE](LICENSE).
