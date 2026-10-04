import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Must be set before `import main`: the engine is created at db.init_app() time.
_TMP_DIR = tempfile.mkdtemp(prefix='wordpuzzle-tests-')
os.environ['WORDPUZZLE_DATABASE_URI'] = 'sqlite:///' + (Path(_TMP_DIR) / 'test.db').as_posix()

import main  # noqa: E402
from models import db, User  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402


@pytest.fixture
def app():
    main.app.config['TESTING'] = True
    with main.app.app_context():
        db.drop_all()
        main.setup_database()
        yield main.app
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    def _make(username, level='primary', password='password123', is_admin=False):
        user = User(username=username, password_hash=generate_password_hash(password),
                    level=level, is_admin=is_admin)
        db.session.add(user)
        db.session.commit()
        return user
    return _make


def login(client, username, password='password123'):
    return client.post('/login', data={'username': username, 'password': password})
