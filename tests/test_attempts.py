from conftest import login
from models import db, Word, TestAttempt, TestAnswer


def week_words(level='primary', week=1):
    return Word.query.filter_by(level=level, week_number=week).all()


def submit(client, attempt_number, answers, week=1):
    return client.post(f'/week/{week}/test/submit',
                       json={'attempt_number': attempt_number, 'answers': answers})


def correct_payload(words):
    return [{'word_id': w.id, 'user_answer': w.word, 'attempt_count': 1} for w in words]


def setup_learner(client, make_user, level='primary', name='kid'):
    make_user(name, level=level)
    login(client, name)


def test_three_attempts_recorded(client, make_user):
    setup_learner(client, make_user)
    words = week_words()
    for n in (1, 2, 3):
        data = submit(client, n, correct_payload(words)).get_json()
        assert data['score'] == 10 and data['total'] == 10
        assert data['attempt_number'] == n
        assert data['redirect_url'].endswith(f'/week/1/results?attempt={n}')
    attempts = TestAttempt.query.order_by(TestAttempt.attempt_number).all()
    assert [a.attempt_number for a in attempts] == [1, 2, 3]
    assert all(a.completed_at is not None and a.total == 10 for a in attempts)


def test_fourth_attempt_blocked(client, make_user):
    setup_learner(client, make_user)
    words = week_words()
    for n in (1, 2, 3):
        submit(client, n, correct_payload(words))
    resp = client.get('/week/1/test')
    assert resp.status_code == 302 and '/week/1/results' in resp.headers['Location']
    data = submit(client, 4, correct_payload(words)).get_json()
    assert 'redirect_url' in data
    assert TestAttempt.query.count() == 3
    assert TestAnswer.query.count() == 30


def test_resubmit_same_attempt_number_writes_nothing(client, make_user):
    setup_learner(client, make_user)
    words = week_words()
    submit(client, 1, correct_payload(words))
    data = submit(client, 1, correct_payload(words)).get_json()
    assert 'redirect_url' in data
    assert TestAttempt.query.count() == 1
    assert TestAnswer.query.count() == 10


def test_blank_answer_is_unattempted(client, make_user):
    setup_learner(client, make_user)
    w = week_words()[0]
    submit(client, 1, [{'word_id': w.id, 'user_answer': '  ', 'attempt_count': 2}])
    ta = TestAnswer.query.filter_by(word_id=w.id).one()
    assert ta.status == 'unattempted'
    assert ta.attempt_count == 0
    assert ta.is_correct is False
    assert ta.user_answer == ''


def test_wrong_answer_is_incorrect(client, make_user):
    setup_learner(client, make_user)
    w = week_words()[0]
    submit(client, 1, [{'word_id': w.id, 'user_answer': 'zzzz', 'attempt_count': 3}])
    ta = TestAnswer.query.filter_by(word_id=w.id).one()
    assert ta.status == 'incorrect'
    assert ta.attempt_count == 3
    assert ta.is_correct is False


def test_missing_words_recorded_as_unattempted(client, make_user):
    setup_learner(client, make_user)
    words = week_words()
    submit(client, 1, correct_payload(words[:3]))
    answers = TestAnswer.query.all()
    assert len(answers) == 10
    assert sum(1 for a in answers if a.status == 'unattempted') == 7
    assert sum(1 for a in answers if a.status == 'correct') == 3


def test_score_counts_only_correct(client, make_user):
    setup_learner(client, make_user)
    words = week_words()
    payload = correct_payload(words[:4])
    payload.append({'word_id': words[4].id, 'user_answer': 'nope', 'attempt_count': 3})
    payload.append({'word_id': words[5].id, 'user_answer': '', 'attempt_count': 0})
    data = submit(client, 1, payload).get_json()
    assert data['score'] == 4 and data['total'] == 10
    assert TestAttempt.query.one().score == 4


def test_attempts_separate_per_level(client, make_user):
    user = make_user('kid', level='primary')
    login(client, 'kid')
    submit(client, 1, correct_payload(week_words('primary')))
    user.level = 'secondary'
    db.session.commit()
    data = submit(client, 1, correct_payload(week_words('secondary'))).get_json()
    assert data['attempt_number'] == 1
    assert TestAttempt.query.count() == 2
    assert client.get('/week/1/test').status_code == 200
