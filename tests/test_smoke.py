from pathlib import Path

from models import db, User, Word
from words_data import PRIMARY_WORDS, SECONDARY_WORDS
from conftest import login


def test_fresh_db_seeds_words(app):
    expected = sum(len(w['words']) for w in PRIMARY_WORDS + SECONDARY_WORDS)
    assert Word.query.count() == expected


def test_admin_exists(app):
    assert User.query.filter_by(username='admin', is_admin=True).first() is not None


def test_register_login_and_plan(client):
    resp = client.post('/register', data={
        'username': 'kid1', 'password': 'secret12',
        'confirm_password': 'secret12', 'level': 'primary'})
    assert resp.status_code == 302
    assert login(client, 'kid1', 'secret12').status_code == 302
    assert client.get('/plan').status_code == 200


def test_make_user_and_login(client, make_user):
    make_user('kid2', level='secondary')
    login(client, 'kid2')
    assert client.get('/plan').status_code == 200


def test_not_using_real_database(app):
    db_file = Path(db.engine.url.database).resolve()
    real = (Path(__file__).resolve().parent.parent / 'instance' / 'wordpuzzle.db').resolve()
    assert db_file != real
