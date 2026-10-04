import json
import os
import random
import shutil
import sys
from datetime import datetime
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from models import (db, User, Word, TestAttempt, TestAnswer,
                    STATUS_CORRECT, STATUS_INCORRECT, STATUS_UNATTEMPTED)
from words_data import PRIMARY_WORDS, SECONDARY_WORDS, WordDataError, validate_word_data

app = Flask(__name__)
app.secret_key = 'wordpuzzle_gep_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('WORDPUZZLE_DATABASE_URI', 'sqlite:///wordpuzzle.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


WEEKS_PER_LEVEL = {'primary': 30, 'secondary': 20}
WORDS_PER_WEEK = 10
MAX_ATTEMPTS = 3
MAX_TRIES_PER_WORD = 3


def setup_database():
    problems = validate_word_data(PRIMARY_WORDS, SECONDARY_WORDS,
                                 weeks=WEEKS_PER_LEVEL, words_per_week=WORDS_PER_WEEK)
    if problems:
        raise WordDataError(problems)
    if _has_legacy_test_schema():
        # One-time wipe: only possible while the old table layout is present.
        backup_path = _backup_sqlite_db()
        TestAnswer.__table__.drop(db.engine)
        TestAttempt.__table__.drop(db.engine)
        app.logger.warning('Upgraded test history schema; old attempts removed; backup at %s',
                           backup_path)
    db.create_all()
    _add_missing_words()
    _ensure_admin()


def _has_legacy_test_schema():
    insp = inspect(db.engine)
    if not insp.has_table('test_attempt'):
        return False
    return 'attempt_number' not in {c['name'] for c in insp.get_columns('test_attempt')}


def _backup_sqlite_db():
    url = db.engine.url
    if url.get_backend_name() != 'sqlite' or not url.database or not os.path.exists(url.database):
        return None
    backup_path = f"{url.database}.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(url.database, backup_path)
    return backup_path


def _add_missing_words():
    existing = {(level, word.lower()) for level, word in db.session.query(Word.level, Word.word)}
    for level_name, data in [('primary', PRIMARY_WORDS), ('secondary', SECONDARY_WORDS)]:
        for week_data in data:
            for w in week_data['words']:
                if (level_name, w['word'].lower()) in existing:
                    continue
                db.session.add(Word(
                    word=w['word'],
                    pos=w.get('pos', ''),
                    meaning=w['meaning'],
                    sentence=w.get('sentence', ''),
                    synonyms=json.dumps(w.get('synonyms', [])),
                    antonyms=json.dumps(w.get('antonyms', [])),
                    week_number=week_data['week'],
                    theme=week_data['theme'],
                    level=level_name
                ))
    db.session.commit()


def _ensure_admin():
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            is_admin=True,
            level='primary'
        )
        db.session.add(admin)
        db.session.commit()


def weeks_for_level(level):
    return WEEKS_PER_LEVEL[level]


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('plan'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('plan'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(request.args.get('next') or url_for('plan'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('plan'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')
        level    = request.form.get('level', 'primary')
        if not username or not password or not confirm:
            flash('All fields are required.', 'danger')
        elif len(username) < 3:
            flash('Username must be at least 3 characters.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
        else:
            level = level if level in ('primary', 'secondary') else 'primary'
            db.session.add(User(
                username=username,
                password_hash=generate_password_hash(password),
                level=level
            ))
            db.session.commit()
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ── Level selection ───────────────────────────────────────────────────────────

@app.route('/select-level', methods=['GET', 'POST'])
@login_required
def select_level():
    if request.method == 'POST':
        level = request.form.get('level', 'primary')
        current_user.level = level if level in ('primary', 'secondary') else 'primary'
        db.session.commit()
        flash(f'Level switched to {current_user.level.capitalize()}.', 'success')
        return redirect(url_for('plan'))
    return render_template('select_level.html', current_level=current_user.level)


def get_attempts(user_id, level, week_num):
    return TestAttempt.query.filter_by(
        user_id=user_id, level=level, week_number=week_num
    ).order_by(TestAttempt.attempt_number).all()


def _word_dict(w):
    return {
        'id': w.id, 'word': w.word, 'pos': w.pos, 'meaning': w.meaning,
        'sentence': w.sentence,
        'synonyms': json.loads(w.synonyms) if w.synonyms else [],
        'antonyms': json.loads(w.antonyms) if w.antonyms else []
    }


# ── Weekly plan ───────────────────────────────────────────────────────────────

@app.route('/plan')
@login_required
def plan():
    level = current_user.level
    total_weeks = weeks_for_level(level)
    attempts_by_week = {}
    for a in (TestAttempt.query.filter_by(user_id=current_user.id, level=level)
              .order_by(TestAttempt.attempt_number).all()):
        attempts_by_week.setdefault(a.week_number, []).append(a)
    week_list = []
    for wn in range(1, total_weeks + 1):
        words = Word.query.filter_by(level=level, week_number=wn).all()
        theme = words[0].theme if words else ''
        week_attempts = attempts_by_week.get(wn, [])
        latest = week_attempts[-1] if week_attempts else None
        week_list.append({
            'week_number': wn,
            'theme': theme,
            'word_count': len(words),
            'attempts_used': len(week_attempts),
            'latest_score': latest.score if latest else None,
            'latest_total': latest.total if latest else None,
            'completed': len(week_attempts) > 0
        })
    return render_template('plan.html', weeks=week_list, level=level,
                           max_attempts=MAX_ATTEMPTS)


# ── Week detail ───────────────────────────────────────────────────────────────

@app.route('/week/<int:week_num>')
@login_required
def week_view(week_num):
    level = current_user.level
    if week_num < 1 or week_num > weeks_for_level(level):
        flash('Week not found.', 'danger')
        return redirect(url_for('plan'))
    words = Word.query.filter_by(level=level, week_number=week_num).all()
    if not words:
        flash('No words found for this week.', 'warning')
        return redirect(url_for('plan'))
    attempts = get_attempts(current_user.id, level, week_num)
    return render_template('week.html', words=[_word_dict(w) for w in words],
                           week_num=week_num, theme=words[0].theme, level=level,
                           attempts=attempts, attempts_used=len(attempts),
                           max_attempts=MAX_ATTEMPTS,
                           latest=attempts[-1] if attempts else None,
                           can_retake=len(attempts) < MAX_ATTEMPTS)


# ── Test ──────────────────────────────────────────────────────────────────────

@app.route('/week/<int:week_num>/test')
@login_required
def week_test(week_num):
    level = current_user.level
    if week_num < 1 or week_num > weeks_for_level(level):
        flash('Week not found.', 'danger')
        return redirect(url_for('plan'))
    attempts = get_attempts(current_user.id, level, week_num)
    if len(attempts) >= MAX_ATTEMPTS:
        flash(f'You have used all {MAX_ATTEMPTS} attempts for this week.', 'info')
        return redirect(url_for('week_results', week_num=week_num))
    words = Word.query.filter_by(level=level, week_number=week_num).all()
    if not words:
        flash('No words found.', 'warning')
        return redirect(url_for('plan'))
    random.shuffle(words)
    return render_template('test.html', words=[_word_dict(w) for w in words],
                           week_num=week_num, theme=words[0].theme, level=level,
                           attempt_number=len(attempts) + 1, max_attempts=MAX_ATTEMPTS)


@app.route('/week/<int:week_num>/test/submit', methods=['POST'])
@login_required
def week_test_submit(week_num):
    level = current_user.level
    results_url = url_for('week_results', week_num=week_num)
    data = request.get_json(silent=True) or {}
    attempts = get_attempts(current_user.id, level, week_num)
    if len(attempts) >= MAX_ATTEMPTS or data.get('attempt_number') != len(attempts) + 1:
        return jsonify({'redirect_url': results_url})  # duplicate or stale submit: no write
    words = Word.query.filter_by(level=level, week_number=week_num).all()
    if not words:
        return jsonify({'redirect_url': results_url})
    submitted = {}
    for a in data.get('answers') or []:
        if isinstance(a, dict):
            submitted[a.get('word_id')] = a
    attempt = TestAttempt(
        user_id=current_user.id, week_number=week_num, level=level,
        attempt_number=len(attempts) + 1, score=0, total=len(words)
    )
    db.session.add(attempt)
    score = 0
    for word in words:
        a = submitted.get(word.id)
        text = str(a.get('user_answer') or '').strip() if a else ''
        if text == '':
            status = STATUS_UNATTEMPTED
            tries = 0
        else:
            status = STATUS_CORRECT if text.lower() == word.word.lower() else STATUS_INCORRECT
            try:
                tries = max(1, min(MAX_TRIES_PER_WORD, int(a.get('attempt_count', 1))))
            except (TypeError, ValueError):
                tries = 1
        if status == STATUS_CORRECT:
            score += 1
        attempt.answers.append(TestAnswer(
            word_id=word.id, user_answer=text, status=status,
            is_correct=(status == STATUS_CORRECT), attempt_count=tries
        ))
    attempt.score = score
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()  # lost a race with a parallel submit of the same attempt
        return jsonify({'redirect_url': results_url})
    return jsonify({'score': score, 'total': len(words),
                    'attempt_number': attempt.attempt_number,
                    'redirect_url': url_for('week_results', week_num=week_num,
                                            attempt=attempt.attempt_number)})


@app.route('/week/<int:week_num>/results')
@login_required
def week_results(week_num):
    level = current_user.level
    attempts = get_attempts(current_user.id, level, week_num)
    if not attempts:
        flash('No completed test found. Take the test first.', 'warning')
        return redirect(url_for('week_test', week_num=week_num))
    wanted = request.args.get('attempt', type=int)
    if wanted is None:
        attempt = attempts[-1]
    else:
        attempt = next((a for a in attempts if a.attempt_number == wanted), None)
        if attempt is None:
            flash('That attempt was not found.', 'warning')
            return redirect(url_for('week_results', week_num=week_num))
    rows = [{
        'word': ta.word.word, 'pos': ta.word.pos, 'meaning': ta.word.meaning,
        'user_answer': ta.user_answer, 'status': ta.status,
        'attempt_count': ta.attempt_count
    } for ta in TestAnswer.query.filter_by(attempt_id=attempt.id).all() if ta.word]
    history = []
    for a in attempts:
        counts = {STATUS_CORRECT: 0, STATUS_INCORRECT: 0, STATUS_UNATTEMPTED: 0}
        for ta in a.answers:
            counts[ta.status] = counts.get(ta.status, 0) + 1
        history.append({'attempt': a, 'correct': counts[STATUS_CORRECT],
                        'incorrect': counts[STATUS_INCORRECT],
                        'unattempted': counts[STATUS_UNATTEMPTED]})
    current_counts = next(h for h in history if h['attempt'].id == attempt.id)
    first = Word.query.filter_by(level=level, week_number=week_num).first()
    return render_template('results.html', attempt=attempt, result_rows=rows,
                           week_num=week_num, theme=first.theme if first else '', level=level,
                           attempts=history, counts=current_counts,
                           max_attempts=MAX_ATTEMPTS,
                           can_retake=len(attempts) < MAX_ATTEMPTS)


# ── Dictionary API proxy ──────────────────────────────────────────────────────

@app.route('/api/word/<word>')
@login_required
def api_word(word):
    try:
        r = requests.get(
            f'https://api.dictionaryapi.dev/api/v2/entries/en/{word}', timeout=5
        )
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502


# ── Admin dashboard ───────────────────────────────────────────────────────────

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Admins only.', 'danger')
        return redirect(url_for('plan'))
    from collections import defaultdict
    users    = User.query.all()
    attempts = TestAttempt.query.all()
    answers  = TestAnswer.query.all()
    user_stats = []
    for u in users:
        ua = [a for a in attempts if a.user_id == u.id]
        user_stats.append({
            'username': u.username, 'level': u.level, 'is_admin': u.is_admin,
            'weeks_completed': len(ua),
            'total_score': sum(a.score for a in ua),
            'total_possible': sum(a.total for a in ua),
            'created_at': u.created_at
        })
    week_scores = defaultdict(list)
    for a in attempts:
        if a.total > 0:
            week_scores[(a.level, a.week_number)].append(a.score / a.total * 100)
    per_week = [{
        'level': lv, 'week_number': wn,
        'average_pct': round(sum(sc) / len(sc), 1), 'count': len(sc)
    } for (lv, wn), sc in sorted(week_scores.items())]
    correct = sum(1 for a in answers if a.is_correct)
    return render_template('admin.html',
                           total_users=len(users),
                           user_stats=user_stats,
                           per_week_averages=per_week,
                           total_correct=correct,
                           total_incorrect=len(answers) - correct)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    try:
        with app.app_context():
            setup_database()
    except WordDataError as err:
        for problem in err.problems:
            print(problem, file=sys.stderr)
        sys.exit(1)
    app.run(debug=True)
