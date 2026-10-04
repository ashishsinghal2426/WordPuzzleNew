import re
import shutil
import subprocess

import pytest

from conftest import login
from models import Word


def take(client, n, words, correct=10):
    answers = [{'word_id': w.id, 'user_answer': w.word if i < correct else 'zzz',
                'attempt_count': 1 if i < correct else 3} for i, w in enumerate(words)]
    return client.post('/week/1/test/submit', json={'attempt_number': n, 'answers': answers})


def learner(client, make_user):
    make_user('kid')
    login(client, 'kid')
    return Word.query.filter_by(level='primary', week_number=1).all()


def test_plan_shows_latest_score_and_attempt_count(client, make_user):
    words = learner(client, make_user)
    take(client, 1, words, correct=3)
    take(client, 2, words, correct=8)
    html = client.get('/plan').get_data(as_text=True)
    assert 'Latest 8/10' in html
    assert '2 of 3 attempts' in html


def test_week_page_hides_retake_after_three(client, make_user):
    words = learner(client, make_user)
    take(client, 1, words)
    html = client.get('/week/1').get_data(as_text=True)
    assert 'Take test again' in html and 'Attempt 1 of 3 used' in html
    take(client, 2, words)
    take(client, 3, words)
    html = client.get('/week/1').get_data(as_text=True)
    assert 'Take test again' not in html
    assert 'All 3 attempts used' in html


def test_week_page_no_attempts(client, make_user):
    learner(client, make_user)
    html = client.get('/week/1').get_data(as_text=True)
    assert 'You have 3 attempts' in html and 'Start test' in html


def test_results_lists_attempts_and_selects_one(client, make_user):
    words = learner(client, make_user)
    take(client, 1, words, correct=2)
    take(client, 2, words, correct=9)
    html = client.get('/week/1/results').get_data(as_text=True)
    assert 'Attempt 2 of 3' in html
    assert 'Your attempts' in html
    assert '?attempt=1' in html and '?attempt=2' in html
    html1 = client.get('/week/1/results?attempt=1').get_data(as_text=True)
    assert 'Attempt 1 of 3' in html1
    assert '2 / 10' in html1
    assert 'class="current"' in html1


def test_results_unknown_attempt_redirects(client, make_user):
    words = learner(client, make_user)
    take(client, 1, words)
    resp = client.get('/week/1/results?attempt=3')
    assert resp.status_code == 302


def test_results_shows_unattempted(client, make_user):
    learner(client, make_user)
    client.post('/week/1/test/submit', json={'attempt_number': 1, 'answers': []})
    html = client.get('/week/1/results').get_data(as_text=True)
    assert 'Not attempted' in html


@pytest.mark.skipif(shutil.which('node') is None, reason='node not installed')
def test_test_page_script_is_valid_js(client, make_user, tmp_path):
    learner(client, make_user)
    html = client.get('/week/1/test').get_data(as_text=True)
    assert 'id="skip-btn"' in html and 'Attempt 1 of 3' in html
    scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
    assert scripts
    f = tmp_path / 'test_page.js'
    f.write_text(scripts[-1], encoding='utf-8')
    result = subprocess.run(['node', '--check', str(f)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def admin_page(client, make_user):
    words = learner(client, make_user)
    take(client, 1, words, correct=10)
    take(client, 2, words, correct=4)
    client.post('/week/1/test/submit', json={'attempt_number': 3, 'answers': []})
    client.get('/logout')
    make_user('boss', is_admin=True)
    login(client, 'boss')
    return client.get('/admin').get_data(as_text=True)


def test_admin_learner_progress(client, make_user):
    html = admin_page(client, make_user)
    assert '1 / 30' in html and '3%' in html
    assert '3 / 90 (3%)' in html


def test_admin_test_details_rows(client, make_user):
    html = admin_page(client, make_user)
    rows = re.findall(r'<tr class="attempt-row">(.*?)</tr>', html, re.S)
    assert len(rows) == 3
    cells = [re.findall(r'<td[^>]*>(.*?)</td>', r, re.S) for r in rows]
    cells = [[c.strip() for c in row] for row in cells]
    assert [c[3] for c in cells] == ['1', '2', '3']
    assert cells[0][5:] == ['10', '0', '0', '100%']
    assert cells[1][5:] == ['4', '6', '0', '40%']
    assert cells[2][5:] == ['0', '0', '10', '0%']


def test_admin_unattempted_card(client, make_user):
    html = admin_page(client, make_user)
    m = re.search(r'Unattempted</div><div class="score unattempted">(\d+)<', html)
    assert m and m.group(1) == '10'


def test_admin_non_admin_redirected(client, make_user):
    learner(client, make_user)
    assert client.get('/admin').status_code == 302
