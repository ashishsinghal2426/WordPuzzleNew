# Technical implementation plan: ten-words-per-week

| | |
|---|---|
| Branch | `claude/feature/ten-words-per-week` |
| Spec | `.claude/_specs/ten-words-per-week.md` |
| Issue | https://github.com/ashishsinghal2426/WordPuzzleNew/issues/1 (description + owner comments) |
| Status | **For review. Nothing implemented yet.** |
| Implemented by | Claude Code, on the branch above, one task per commit (section 7) |
| Reviewed by | Repo owner: approves each commit message (per CLAUDE.md) and reviews the full word list once, at the end |

---

## 1. Requirements baseline

The issue description (the spec) plus the owner's decisions. Where they differ, the later decision wins.

| # | Requirement | Source |
|---|---|---|
| R1 | All 30 Primary and 20 Secondary weeks filled, **exactly 10 words** each (500 words) | Spec |
| R2 | Themes and words friendly to children aged 10–12 (theme table in spec) | Spec |
| R3 | App **refuses to start** if the word data breaks R1 | Spec |
| R4 | Existing databases get missing words **added**; users and words kept | Spec |
| R5 | Existing (pre-go-live) test history is wiped **once**. Never wiped again after go-live | Spec + answer 2 |
| R6 | **Max 3 attempts per week**, per learner, per level | Issue comment |
| R7 | Every attempt stored with week, attempt number and timestamp | Spec |
| R8 | Each question in an attempt is recorded as **correct / incorrect / unattempted** | Issue comment |
| R9 | Test page has a **Skip** button | Answer 1 |
| R10 | Plan page shows the **latest** score | Issue comment |
| R11 | Admin per-week averages: calculation unchanged | Issue comment |
| R12 | Admin learner view: **tests completed / number of weeks with a percentage**, plus a **table of every test with its score percentage** | Answer 3 |
| R13 | Database **backed up** automatically before the one-time wipe | Answer 4 |
| R14 | Word list reviewed by the owner **once, at the end** (not in batches) | Answer 5 |
| R15 | `pytest` added to `requirements.txt` | Answer 6 |

**Terms:** a **try** is one guess at one word (max 3 per word, existing). An **attempt** is one full sitting of a week's test (max 3 per week, new).

---

## 2. Codebase analysis

### 2.1 Files and impact

| File | Lines | Role today | Impact |
|---|---|---|---|
| `main.py` | 338 | App config, all routes, `init_db()` seeding | **Heavy**: config, startup, 6 routes |
| `models.py` | 46 | 4 SQLAlchemy models | **Medium**: 2 new columns, 1 constraint |
| `words_data.py` | 93 | 5 sample weeks × 5 words | **Replaced** by a `words_data/` package (500 words + validator) |
| `templates/test.html` | 91 | Client-side test, 3 tries per word, JSON submit | **Medium**: Skip button, attempt number, submit guard |
| `templates/week.html` | 55 | Study page, one-shot test banner (lines 7–15) | **Small**: attempts banner |
| `templates/results.html` | 31 | One attempt's breakdown | **Medium**: status column, counts, attempt history |
| `templates/plan.html` | 19 | Week grid, "Completed" badge | **Small**: latest score + attempts used |
| `templates/admin.html` | 53 | Totals, user table, per-week averages | **Medium**: new user table, new test-details table |
| `static/css/style.css` | 119 | Styles | **Small**: 3–4 new rules |
| `requirements.txt` | 5 | Runtime deps | Add `pytest` |
| `README.md`, `CLAUDE.md` | n/a | Docs | Update |
| `.claude/_specs/ten-words-per-week.md` | n/a | Spec | Sync with comments and answers |
| `templates/base.html`, `login.html`, `register.html`, `select_level.html` | n/a | Layout, auth pages | **No change** |
| `.gitignore` | n/a | Already ignores `instance/` and `*.db` (backups land in `instance/`) | **No change** |
| `tests/` | n/a | Does not exist | **New** |

### 2.2 Current behaviour that must change (with locations)

| Location | Current behaviour | Problem for this feature |
|---|---|---|
| `main.py:12` | DB URI hardcoded to `sqlite:///wordpuzzle.db` | Tests cannot use a temporary DB |
| `main.py:25–51` `init_db()` | Seeds words only if the `Word` table is empty | Existing DBs never get new words (R4) |
| `main.py:54–55` `weeks_for_level()` | Returns hardcoded 30 / 20 | Nothing checks the data matches (R3) |
| `main.py:142–145` `plan()` | `completed_weeks` set only | No latest score or attempt count (R10) |
| `main.py:178–183` `week_view()` | Fetches one latest attempt | Needs the full attempt list (R6) |
| `main.py:195–199` `week_test()` | Blocks if **any** attempt exists | Must allow up to 3 (R6) |
| `main.py:219–222` `week_test_submit()` | Blocks if any attempt exists | Must allow up to 3, and reject duplicates |
| `main.py:235–247` `week_test_submit()` | One `TestAnswer` per *submitted* answer; `total = len(valid_words)` | Unsubmitted words are not recorded; no status (R8) |
| `main.py:258–260` `week_results()` | Latest attempt by `completed_at` only | Needs `?attempt=n` and history (R7) |
| `main.py:266` `week_results()` | `Word.query.get()` per row (N+1, legacy API) | Use the existing `TestAnswer.word` relationship |
| `main.py:305–313` `admin_dashboard()` | `weeks_completed = len(attempts)`; `total_score/total_possible` | Overcounts with retakes; replaced by R12 |
| `main.py:322–328` `admin_dashboard()` | `incorrect = len(answers) - correct` | Would count unattempted as incorrect (R8) |
| `main.py:333–337` `__main__` | `create_all()` + `init_db()` | No validation, upgrade or backup (R3, R5, R13) |
| `models.py:28–36` `TestAttempt` | No attempt number | R6, R7 |
| `models.py:38–45` `TestAnswer` | `is_correct` only | R8 |
| `templates/test.html:13–14` | Answer is required to move on | No way to skip (R9) |
| `templates/test.html:60` | Posts `{answers}` only | Server cannot detect a resubmit |
| `templates/week.html:12` | Text says "You only get one attempt" | Wrong after R6 |
| `templates/results.html:24` | Correct / Incorrect only | R8 |
| `templates/admin.html:16–24` | "Weeks done" + "Score" columns | Replaced by R12 |

### 2.3 Database facts

- SQLite through Flask-SQLAlchemy 3.1.1. The file lives at `instance/wordpuzzle.db`: Flask-SQLAlchemy resolves relative SQLite paths against `app.instance_path`.
- There is **no migration tool**. `db.create_all()` creates missing tables but never alters existing ones, so new columns on existing tables need explicit handling (section 3.2).
- The owner's local DB today has the old schema, with 2 users, 25 words, 1 attempt and 5 answers. This is the upgrade path to verify.
- SQLAlchemy is not pinned (the venv resolved 2.1.3). `Query.get()` is legacy in 2.x; new code uses `db.session.get()`.

---

## 3. Target design

### 3.1 Data model (`models.py`)

```
TestAttempt
  + attempt_number  Integer, NOT NULL            # 1..3, per (user, level, week)
  + __table_args__ = UniqueConstraint(user_id, level, week_number, attempt_number,
                                      name='uq_attempt_user_level_week_number')
  (completed_at already exists and is the attempt timestamp)

TestAnswer
  + status  String(12), NOT NULL, default 'unattempted'   # 'correct' | 'incorrect' | 'unattempted'
  (is_correct kept, always == (status == 'correct'))
  (attempt_count kept = tries used; 0 when unattempted)
```

Module-level constants in `models.py`: `STATUS_CORRECT`, `STATUS_INCORRECT`, `STATUS_UNATTEMPTED`.

### 3.2 Startup flow: `setup_database()` in `main.py`

It replaces the `__main__` body and is callable from tests. Order:

```
setup_database():
  1. problems = validate_word_data(PRIMARY_WORDS, SECONDARY_WORDS,
                                   weeks=WEEKS_PER_LEVEL, words_per_week=WORDS_PER_WEEK)
     if problems: raise WordDataError(problems)            # R3
  2. if _has_legacy_test_schema():                          # test_attempt exists AND lacks attempt_number
        _backup_sqlite_db()                                 # R13: copy to instance/wordpuzzle.db.bak-YYYYmmdd-HHMMSS
        drop test_answer, then test_attempt                 # R5: one-time wipe
        log "Upgraded test history schema; old attempts removed; backup at <path>"
  3. db.create_all()                                        # creates new-schema tables; user/word untouched
  4. _add_missing_words()                                   # R4: insert rows whose (level, lower(word)) is absent
  5. _ensure_admin()                                        # existing admin creation, unchanged
```

Why the wipe is once only (R5): step 2 fires only when the *old* table layout is present. After it runs, `create_all()` builds the new layout, so on every later start, including after go-live, the check is false. A brand-new install has no `test_attempt` table, so it never wipes either.

- `__main__` calls `setup_database()` inside `app.app_context()`. It catches `WordDataError`, prints each problem, and exits with code 1.
- Backup only runs for a SQLite URL whose file exists. The path comes from `db.engine.url.database`.

### 3.3 Word data package

```
words_data/
  __init__.py      exports PRIMARY_WORDS, SECONDARY_WORDS, validate_word_data, WordDataError
  primary.py       PRIMARY_WORDS: 30 weeks × 10 words
  secondary.py     SECONDARY_WORDS: 20 weeks × 10 words
  validation.py    validate_word_data(primary, secondary, weeks, words_per_week) -> list[str]
```

`from words_data import PRIMARY_WORDS, SECONDARY_WORDS` (`main.py:8`) keeps working. The current `words_data.py` is deleted; its 25 words move into week 1–3 / 1–2 of the new files unchanged.

`validate_word_data` returns a human-readable problem per failure:

| Check | Example message |
|---|---|
| Week count | `primary: expected 30 weeks, found 29` |
| Week numbering 1..N, no gaps or duplicates | `secondary: week 7 missing` |
| Theme present | `primary week 4: missing theme` |
| Exactly 10 words | `primary week 12: expected 10 words, found 9` |
| Required fields `word, pos, meaning, sentence` non-empty | `secondary week 3 'resilient': missing sentence` |
| Word is letters only (hyphen allowed) | `primary week 5 'ice cream': word must be letters only` |
| Sentence contains the word (case-insensitive, whole word) | `primary week 2 'blossom': sentence does not contain the word` |
| No duplicate word within a level | `primary: 'gentle' appears in weeks 2 and 14` |

The letters-only rule protects the test page's `RegExp` blanking (`test.html:30`) and exact-match grading.

Constants in `main.py`: `WEEKS_PER_LEVEL = {'primary': 30, 'secondary': 20}`, `WORDS_PER_WEEK = 10`, `MAX_ATTEMPTS = 3`. `weeks_for_level()` (`main.py:54`) returns `WEEKS_PER_LEVEL[level]`.

### 3.4 Attempt lifecycle

```
GET /week/<n>/test
  attempts = get_attempts(user, level, n)
  if len(attempts) >= MAX_ATTEMPTS -> flash + redirect /week/<n>/results
  render test.html with attempt_number = len(attempts) + 1, max_attempts

POST /week/<n>/test/submit   body: {attempt_number, answers: [{word_id, user_answer, attempt_count}]}
  attempts = get_attempts(...)
  if len(attempts) >= MAX_ATTEMPTS or body.attempt_number != len(attempts) + 1:
      return {redirect_url: results}            # duplicate/resubmit: no write
  create TestAttempt(attempt_number=len+1, total=WORDS in week)
  for EVERY word in the week (not just submitted ones):
      a = submitted answer for word_id (if any)
      text = a.user_answer.strip() if a else ''
      status = unattempted if text == ''
               correct     if text.lower() == word.lower()
               incorrect   otherwise
      tries = 0 if unattempted else clamp(a.attempt_count, 1, 3)
      add TestAnswer(status, is_correct=(status==correct), user_answer=text, attempt_count=tries)
  score = count(correct)
  commit; on IntegrityError (unique constraint race) -> rollback, return {redirect_url}
  return {score, total, attempt_number, redirect_url: results?attempt=<n>}
```

Skip semantics (R9):
- Skip with **0 tries** sends `user_answer: ''`, so the word is **unattempted**.
- Skip **after one or more wrong tries** sends the last wrong answer, so the word is **incorrect**. The learner did attempt it.

Grading stays server-side. The client check only drives the UI.

### 3.5 Admin data (R11, R12)

Built in `admin_dashboard()`:

- **Totals cards:** users, correct, incorrect, unattempted, from `TestAnswer.status` counts. This fixes `main.py:322–328`.
- **Learner progress table:** one row per user, for their **current level**:

  | Column | Value |
  |---|---|
  | Username, Level | unchanged |
  | Tests completed | `distinct weeks with ≥1 attempt` / `weeks_for_level(level)`, e.g. `4 / 30` |
  | Completion % | `round(completed / weeks * 100)`, e.g. `13%` |
  | Attempts used | `attempts` / `weeks × 3`, with %, e.g. `6 / 90 (7%)` |
  | Joined | unchanged |

  The old `total_score / total_possible` column is removed (answer 3: "no").
- **Test details table** (new): one row per attempt, sorted by user, level, week and attempt number.

  | User | Level | Week | Attempt | Date (UTC) | Correct | Incorrect | Unattempted | Score % |
  |---|---|---|---|---|---|---|---|---|

  Status counts come from **one** grouped query (`TestAnswer.attempt_id, status, count(*)`), not a query per row.
- **Average score per week:** calculation unchanged (R11).

---

## 4. File-by-file changes

### 4.1 `main.py`

| Where | Change |
|---|---|
| Imports (1–8) | Add `os`, `shutil`, `datetime`, `sqlalchemy.inspect`, `sqlalchemy.func`, `sqlalchemy.exc.IntegrityError`. Import `validate_word_data, WordDataError` from `words_data`. Import the status constants from `models` |
| Config (12) | `os.environ.get('WORDPUZZLE_DATABASE_URI', 'sqlite:///wordpuzzle.db')` |
| New constants (after 17) | `WEEKS_PER_LEVEL`, `WORDS_PER_WEEK`, `MAX_ATTEMPTS` |
| `load_user` (21–22) | `db.session.get(User, int(user_id))` (legacy API cleanup, same behaviour) |
| `init_db` (25–51) | **Replaced** by `setup_database()` plus private helpers `_has_legacy_test_schema()`, `_backup_sqlite_db()`, `_add_missing_words()`, `_ensure_admin()` (section 3.2) |
| `weeks_for_level` (54–55) | Read from `WEEKS_PER_LEVEL` |
| New helper | `get_attempts(user_id, level, week_num)` returns the attempts ordered by `attempt_number` |
| New helper | `_word_dict(w)`: the word-to-dict code duplicated at 172–177 and 205–210, extracted once |
| `plan()` (137–156) | One query for the user's attempts at this level, grouped by week. Each week dict gains `attempts_used` and `latest_score` / `latest_total` (latest = highest `attempt_number`). `completed = attempts_used > 0` |
| `week_view()` (161–183) | Pass `attempts` (list), `attempts_used`, `max_attempts`, `latest`, `can_retake`. Drop `completed` / `attempt` |
| `week_test()` (188–212) | Limit check via `get_attempts` (3.4). Pass `attempt_number`, `max_attempts` |
| `week_test_submit()` (215–251) | Rewritten per section 3.4: duplicate guard, every-word recording, status, `IntegrityError` handling, `attempt_number` in the response |
| `week_results()` (254–275) | Optional `request.args.get('attempt', type=int)`, defaulting to the latest. 404→flash+redirect if that number doesn't exist. Rows use `ta.word` and include `status`. Pass `attempt`, `attempts` (history with per-attempt counts), `counts` (correct/incorrect/unattempted), `can_retake` |
| `admin_dashboard()` (294–328) | Rebuilt per section 3.5. Template variables: `total_users`, `total_correct`, `total_incorrect`, `total_unattempted`, `learner_progress`, `test_details`, `per_week_averages` (unchanged logic) |
| `__main__` (333–337) | `with app.app_context(): setup_database()`, catching `WordDataError` and exiting 1. Then `app.run(debug=True)` |

### 4.2 `models.py`

| Where | Change |
|---|---|
| Top | `STATUS_CORRECT = 'correct'`, `STATUS_INCORRECT = 'incorrect'`, `STATUS_UNATTEMPTED = 'unattempted'` |
| `TestAttempt` (28–36) | Add `attempt_number = db.Column(db.Integer, nullable=False)`, plus `__table_args__` with the unique constraint |
| `TestAnswer` (38–45) | Add `status = db.Column(db.String(12), nullable=False, default=STATUS_UNATTEMPTED)` |

### 4.3 `words_data/` (replaces `words_data.py`)

- `validation.py`: `WordDataError(Exception)` (holds `.problems`) and `validate_word_data(...)` (section 3.3).
- `primary.py`: 30 weeks, themes per the spec table. Weeks 1–3 keep the current 15 words and add 5 each.
- `secondary.py`: 20 weeks, themes per the spec table. Weeks 1–2 keep the current 10 words and add 5 each.
- `__init__.py`: re-exports.

Content rules:
- Ages 10–12; Primary easier than Secondary.
- British spelling (matches "practise", "colour").
- Avoid words whose spelling differs between British and American English, apart from the existing "practise".
- Each sentence uses the exact tested form of the word.
- No duplicate words within a level. Week 30 "Tricky Spellings Review" uses **new** tricky words, not repeats.
- Synonyms and antonyms where sensible.

### 4.4 `templates/test.html`

| Where | Change |
|---|---|
| 5–6 | Heading `Week {{ week_num }} test · Attempt {{ attempt_number }} of {{ max_attempts }}` |
| After 14 | `<button type="button" class="btn btn-secondary btn-block" id="skip-btn">Skip this word</button>` |
| 22–26 | Add `var ATTEMPT_NUMBER = {{ attempt_number }};`, `var lastWrong = '';`, `var submitted = false;` |
| `show()` 33–45 | Reset `lastWrong`; enable the skip button |
| `next()` 47–53 | Also disable the skip button |
| New handler | Skip click: `next(lastWrong)`, so the server gets `''` (unattempted) or the last wrong answer (incorrect) |
| Wrong-answer branch 81–85 | Store `lastWrong = value` |
| `submit()` 55–65 | Return early if `submitted`; set `submitted = true`; body `{attempt_number: ATTEMPT_NUMBER, answers}`. On fetch failure reset `submitted` and show a **Retry** button |

### 4.5 `templates/week.html`

| Where | Change |
|---|---|
| 7–15 | Replaced by an attempts banner, in three states:<br>• **No attempts:** "You have 3 attempts" + **Start test**.<br>• **Some attempts:** "Attempt 1 of 3 used · Latest score 7 / 10" + **View results** + **Take test again** (only if `can_retake`).<br>• **All used:** "All 3 attempts used" + **View results** |

### 4.6 `templates/results.html`

| Where | Change |
|---|---|
| 5–11 | Heading shows "Attempt n of 3". The score card adds three counts: correct, incorrect, unattempted |
| 24 | Result cell uses `r.status` → Correct / Incorrect / Not attempted, with classes `correct` / `incorrect` / `unattempted` |
| 22–23 | Unattempted rows show `—` for answer and tries |
| After table | **Your attempts** table: Attempt, Date (UTC), Correct, Incorrect, Unattempted, Score. Each row links to `?attempt=n`, and the shown attempt is highlighted (`tr.current`). A **Take test again** button if `can_retake` |

### 4.7 `templates/plan.html`

| Where | Change |
|---|---|
| 14 | When `w.completed`: badge `Latest {{ w.latest_score }}/{{ w.latest_total }}` and a muted line `{{ w.attempts_used }} of 3 attempts` |
| 12 | Keep `'Coming soon'` fallback (unused once data is complete, harmless) |

### 4.8 `templates/admin.html`

| Where | Change |
|---|---|
| 6–10 | Add an **Unattempted** card |
| 12–30 | Users table becomes **Learner progress** (columns in 3.5) |
| New card after 30 | **Test details** table (columns in 3.5), with an empty state "No tests taken yet." |
| 32–51 | Per-week averages unchanged |

### 4.9 `static/css/style.css`

Add:
- `.unattempted { color: var(--muted); font-weight: 600; }`
- `tr.current { background: #eef2ff; }`
- `.counts { display: flex; gap: 16px; }` for the results summary
- `.table-scroll { overflow-x: auto; }`, wrapping the wide admin test-details table so the page doesn't scroll sideways on phones

### 4.10 `requirements.txt`

Append `pytest`, pinned to the version installed at implementation time (R15).

### 4.11 Docs

- `README.md`: the features list says one attempt; change it to up to 3 attempts with history, a Skip option and full 30/20-week word lists. Add a "Running tests" section (`.venv/Scripts/python -m pytest`).
- `CLAUDE.md`:
  - Models: `attempt_number`, unique constraint, `status`; tests are no longer one-shot.
  - Word data: the `words_data/` package and validator.
  - Startup: `setup_database()`, one-time upgrade and backup.
  - Testing: pytest replaces "no automated test suite".
  - Gotchas: the hardcoded week counts are now validated.
  - The `WORDPUZZLE_DATABASE_URI` env var.
- `.claude/_specs/ten-words-per-week.md`: apply the issue comments and answers (3 attempts, latest score, statuses, Skip, admin table, averages unchanged).

---

## 5. Tests (`tests/`, pytest)

| File | Contents |
|---|---|
| `tests/conftest.py` | Sets `WORDPUZZLE_DATABASE_URI` to a session temp SQLite file **before** importing `main`. Fixtures:<br>• `app`: `TESTING=True`, `drop_all()`, then `setup_database()` per test<br>• `client`<br>• `make_user(level)`<br>• `login(client, user)`<br>• `OLD_SCHEMA_SQL`: the exact legacy DDL from section 2.3, to build a pre-upgrade DB |
| `tests/test_word_data.py` | Real data: 30/20 weeks numbered 1..N with themes; 10 words per week; required fields; letters-only; sentence contains the word; no duplicates per level; `validate_word_data` returns `[]`.<br>Validator: bad fixtures (9 words, 11 words, gap, duplicate, missing field) each produce the expected message |
| `tests/test_setup_database.py` | Fresh DB seeds 500 words. Second run adds 0 and makes no duplicates. Old-schema DB with 5-word weeks, a user, an attempt and answers is upgraded: user kept, words topped up to 500, old attempt gone, backup file exists. After the upgrade, a new attempt survives another `setup_database()`. Invalid data raises `WordDataError` |
| `tests/test_attempts.py` | Submits create attempts 1, 2, 3 with timestamps and `total == 10`. 4th: `GET /test` redirects and `POST /submit` writes nothing. Resubmitting the same `attempt_number` writes nothing. Blank answer → `unattempted`, 0 tries. Wrong → `incorrect`. Words missing from the payload are recorded as unattempted (10 answers stored). Score counts only correct. Attempts are separate per level |
| `tests/test_pages.py` | Plan shows the latest score and "n of 3 attempts". Week page hides "Take test again" after 3. Results lists all attempts, and `?attempt=1` shows attempt 1. Admin: 2 attempts on one week give `1 / 30` completed; the test-details table has one row per attempt with the right %; the unattempted card counts correctly. `node --check` on the extracted `test.html` script (skipped if node is absent) |

---

## 6. Verification (manual, after the tests pass)

1. Copy the owner's current `instance/wordpuzzle.db` (old schema, 1 attempt) to a scratch location and point `WORDPUZZLE_DATABASE_URI` at the copy.
2. Start the app and confirm the upgrade log line, the backup file, 500 words, users kept and the old attempt gone.
3. Restart and confirm no second backup or wipe.
4. As a learner, take week 1 three times, using Skip on a word with 0 tries, Skip after 1 wrong try, and one fully wrong word. Check statuses on results, the history table, `?attempt=n` links, plan latest score, week banner states, and the 4th attempt blocked.
5. As admin, check the learner progress row (completed / weeks, %, attempts used) and the test-details rows.
6. Remove one word from a week in a scratch copy of the data and confirm startup exits with the exact level/week message.
7. Phone-width check of the admin and results tables.

---

## 7. Implementation order and commits

Each step is a separate commit using the repo's emoji convention, with the message proposed for approval first.

| # | Step | Files | Commit (proposed) |
|---|---|---|---|
| 1 | Sync spec with issue comments and answers | `.claude/_specs/…` | 📝 docs: sync ten-words-per-week spec with review decisions |
| 2 | Test harness: pytest, DB URI env var, `setup_database()` extracted (behaviour unchanged), conftest | `requirements.txt`, `main.py`, `tests/conftest.py` | ✅ test: add pytest harness and configurable database URI |
| 3 | Validator + tests (TDD) | `words_data/validation.py`, `words_data/__init__.py`, `tests/test_word_data.py` | ✨ feat: validate weekly word data at startup |
| 4 | Full word content (450 new words), then owner review (R14) | `words_data/primary.py`, `words_data/secondary.py`, delete `words_data.py` | ✨ feat: fill all weeks with ten kid-friendly words |
| 5 | Schema, one-time upgrade with backup, adding missing words + tests | `models.py`, `main.py`, `tests/test_setup_database.py` | ✨ feat: upgrade test history schema and add missing words |
| 6 | 3-attempt limit, statuses, submit rewrite + tests | `main.py`, `tests/test_attempts.py` | ✨ feat: allow three attempts per week with per-question status |
| 7 | Templates + CSS: Skip, banners, history, plan | `templates/test.html`, `week.html`, `results.html`, `plan.html`, `style.css`, `tests/test_pages.py` | ✨ feat: show attempts, skip and history in the UI |
| 8 | Admin learner progress + test details | `main.py`, `templates/admin.html`, `tests/test_pages.py` | ✨ feat: admin progress and per-test score tables |
| 9 | Docs | `README.md`, `CLAUDE.md` | 📝 docs: document attempts, word data and tests |
| 10 | Manual verification (section 6), then push and link the issue | n/a | n/a |

---

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| 450 generated words need checking for age-appropriateness and accuracy | Validator enforces structure. Owner reviews the full list at step 4 before later steps build on it |
| One-time wipe deletes data | Fires only on the legacy schema; automatic timestamped backup; log line; covered by tests |
| The wipe running after go-live | Impossible by construction (section 3.2), and a test covers it |
| Double submit / race creates an extra attempt | `attempt_number` check plus DB unique constraint plus client `submitted` flag |
| British/American spelling marked wrong | Content rule avoids variant words. Accepting alternatives is out of scope |
| No migration tool for future changes | Noted in CLAUDE.md. Adopt Flask-Migrate if the schema changes again |
| Unpinned SQLAlchemy | Out of scope. Recommend pinning in a follow-up |

## 9. Out of scope (noted, not changed)

- The test page embeds the answers in the page source (`test.html:22`), as it does today.
- `datetime.utcnow` deprecation warnings on Python 3.12+ (`models.py:13, 35`).
- Hardcoded `secret_key` and admin password (`main.py:11`, `46`), already listed in CLAUDE.md Gotchas.

## 10. One point to confirm

**"Percentage of attempts" in answer 3.** The plan shows **Completion %** (weeks completed ÷ weeks) **and** **Attempts used %** (attempts ÷ weeks × 3) in the learner table. Each test's score % appears in the test-details table. If you meant something else, for example the share of a learner's attempts that were passes, say so before step 8.
