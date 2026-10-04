from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    level = db.Column(db.String(20), default='primary')  # 'primary' or 'secondary'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    attempts = db.relationship('TestAttempt', backref='user', lazy=True)

class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False)
    pos = db.Column(db.String(50))
    meaning = db.Column(db.Text, nullable=False)
    sentence = db.Column(db.Text)
    synonyms = db.Column(db.Text)   # JSON string
    antonyms = db.Column(db.Text)   # JSON string
    week_number = db.Column(db.Integer, nullable=False)
    theme = db.Column(db.String(100))
    level = db.Column(db.String(20), nullable=False)  # 'primary' or 'secondary'

class TestAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    week_number = db.Column(db.Integer, nullable=False)
    level = db.Column(db.String(20), nullable=False)
    score = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    answers = db.relationship('TestAnswer', backref='attempt', lazy=True)

class TestAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('test_attempt.id'), nullable=False)
    word_id = db.Column(db.Integer, db.ForeignKey('word.id'), nullable=False)
    user_answer = db.Column(db.Text)
    is_correct = db.Column(db.Boolean, default=False)
    attempt_count = db.Column(db.Integer, default=1)
    word = db.relationship('Word')
