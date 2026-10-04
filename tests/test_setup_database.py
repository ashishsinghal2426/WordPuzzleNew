import glob

import pytest
from sqlalchemy import inspect, text

import main
from models import db, User, Word, TestAttempt, TestAnswer
from words_data import PRIMARY_WORDS

# Exact DDL of the owner's pre-upgrade database.
OLD_SCHEMA_SQL = [
    "CREATE TABLE user (id INTEGER NOT NULL, username VARCHAR(80) NOT NULL, password_hash VARCHAR(200) NOT NULL, is_admin BOOLEAN, level VARCHAR(20), created_at DATETIME, PRIMARY KEY (id), UNIQUE (username))",
    "CREATE TABLE word (id INTEGER NOT NULL, word VARCHAR(100) NOT NULL, pos VARCHAR(50), meaning TEXT NOT NULL, sentence TEXT, synonyms TEXT, antonyms TEXT, week_number INTEGER NOT NULL, theme VARCHAR(100), level VARCHAR(20) NOT NULL, PRIMARY KEY (id))",
    "CREATE TABLE test_attempt (id INTEGER NOT NULL, user_id INTEGER NOT NULL, week_number INTEGER NOT NULL, level VARCHAR(20) NOT NULL, score INTEGER, total INTEGER, completed_at DATETIME, PRIMARY KEY (id), FOREIGN KEY(user_id) REFERENCES user (id))",
    "CREATE TABLE test_answer (id INTEGER NOT NULL, attempt_id INTEGER NOT NULL, word_id INTEGER NOT NULL, user_answer TEXT, is_correct BOOLEAN, attempt_count INTEGER, PRIMARY KEY (id), FOREIGN KEY(attempt_id) REFERENCES test_attempt (id), FOREIGN KEY(word_id) REFERENCES word (id))",
]


def _backups():
    return glob.glob(str(db.engine.url.database) + '.bak-*')


def _clear_backups():
    import os
    for path in _backups():
        os.remove(path)


def _drop_all_tables():
    db.session.remove()
    with db.engine.begin() as conn:
        names = [r[0] for r in conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))]
        for name in names:
            conn.execute(text(f'DROP TABLE "{name}"'))


def _build_legacy_db():
    """Replace the current DB with the old schema, 5-word weeks, a user and one attempt."""
    _clear_backups()
    _drop_all_tables()
    with db.engine.begin() as conn:
        for ddl in OLD_SCHEMA_SQL:
            conn.execute(text(ddl))
        conn.execute(text(
            "INSERT INTO user (id, username, password_hash, is_admin, level) "
            "VALUES (1, 'kid', 'x', 0, 'primary')"))
        for i, w in enumerate(PRIMARY_WORDS[0]['words'][:5], start=1):
            conn.execute(text(
                "INSERT INTO word (id, word, pos, meaning, sentence, synonyms, antonyms, "
                "week_number, theme, level) VALUES (:id, :w, :p, :m, :s, '[]', '[]', 1, :t, 'primary')"),
                {'id': i, 'w': w['word'], 'p': w.get('pos', ''), 'm': w['meaning'],
                 's': w.get('sentence', ''), 't': PRIMARY_WORDS[0]['theme']})
        conn.execute(text(
            "INSERT INTO test_attempt (id, user_id, week_number, level, score, total) "
            "VALUES (1, 1, 1, 'primary', 3, 5)"))
        for i in range(1, 6):
            conn.execute(text(
                "INSERT INTO test_answer (id, attempt_id, word_id, user_answer, is_correct, attempt_count) "
                "VALUES (:i, 1, :i, 'a', 1, 1)"), {'i': i})


def test_fresh_db_seeds_500_words(app):
    assert Word.query.count() == 500


def test_second_run_adds_nothing(app):
    main.setup_database()
    assert Word.query.count() == 500
    keys = {(w.level, w.word.lower()) for w in Word.query.all()}
    assert len(keys) == 500


def test_fresh_install_creates_no_backup(app):
    _clear_backups()
    _drop_all_tables()
    main.setup_database()
    assert _backups() == []
    assert Word.query.count() == 500


def test_legacy_db_is_upgraded(app):
    _build_legacy_db()
    main.setup_database()

    assert User.query.filter_by(username='kid').count() == 1
    assert Word.query.count() == 500
    assert TestAttempt.query.count() == 0
    assert TestAnswer.query.count() == 0
    columns = {c['name'] for c in inspect(db.engine).get_columns('test_attempt')}
    assert 'attempt_number' in columns
    assert len(_backups()) == 1


def test_wipe_happens_only_once(app):
    _build_legacy_db()
    main.setup_database()
    kid = User.query.filter_by(username='kid').one()
    word = Word.query.filter_by(level='primary', week_number=1).first()
    attempt = TestAttempt(user_id=kid.id, week_number=1, level='primary',
                          score=1, total=10, attempt_number=1)
    db.session.add(attempt)
    db.session.flush()
    db.session.add(TestAnswer(attempt_id=attempt.id, word_id=word.id, user_answer='x',
                              is_correct=True, attempt_count=1, status='correct'))
    db.session.commit()

    main.setup_database()

    assert TestAttempt.query.count() == 1
    assert TestAnswer.query.count() == 1
    assert len(_backups()) == 1
