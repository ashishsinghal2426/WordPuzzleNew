# WordPuzzle

A Flask web app for building vocabulary through weekly word sets. Learners pick a level (**Primary**, 30 weeks, or **Secondary**, 20 weeks), study each week's themed word list with meanings, example sentences, synonyms and antonyms, then take a randomized spelling test (up to 3 attempts per week). Every attempt is saved per word, and an admin dashboard shows progress across users and weeks.

## Features

- User registration and login, with a level chosen per learner
- Weekly plan showing progress across all weeks
- Study view per week, with live definitions from [dictionaryapi.dev](https://dictionaryapi.dev)
- Full word lists: 10 words in each of the 30 Primary and 20 Secondary weeks
- Randomized spelling test, up to 3 attempts per week with attempt history, 3 tries per word, and a Skip option
- Score breakdown after each attempt; the plan page shows the latest score
- Admin dashboard with learner progress, per-week averages and a table of every test

## Getting started

```bash
pip install -r requirements.txt
python main.py
```

Open http://localhost:5000. On first run the app creates the SQLite database (`instance/wordpuzzle.db`), loads the words from the `words_data/` package, and creates a default admin account: `admin` / `admin123` (change it before deploying).

The app refuses to start if the word data breaks the rules (30/20 weeks, exactly 10 words each); the problems are printed to stderr.

## Tech stack

Flask · Flask-SQLAlchemy (SQLite) · Flask-Login · Jinja2 · requests

## Project structure

```
main.py           Flask app, routes, and database seeding
models.py         User, Word, TestAttempt, TestAnswer models
words_data/       Weekly word lists (primary, secondary) and the startup validator
tests/            pytest suite
templates/        Jinja2 page templates
static/           CSS and JavaScript
```

## Running tests

```bash
.venv/Scripts/python -m pytest
```

Tests use a temporary database, never `instance/wordpuzzle.db`.

## License

MIT. See [LICENSE](LICENSE).
