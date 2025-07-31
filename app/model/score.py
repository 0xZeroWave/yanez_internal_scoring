from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class AverageScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user_uid.id'), nullable=False)
class UserUID(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer)
    create_at = db.Column(db.DateTime, default= lambda: datetime.now(timezone.utc))
    sessions = db.relationship('ScoreSession', backref='user', cascade="all, delete-orphan")
class ScoreSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_uid.id'), nullable=False)
    avg_final_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    names = db.relationship('NameScore', backref='session', cascade="all, delete-orphan")

class NameScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    final_score = db.Column(db.Float)
    base_score = db.Column(db.Float)
    session_id = db.Column(db.Integer, db.ForeignKey('score_session.id'))
    variations = db.relationship('VariationScore', backref='name_score', cascade="all, delete-orphan")

class VariationScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    variation = db.Column(db.String(128))
    phonetic_score = db.Column(db.Float)
    orthographic_score = db.Column(db.Float)
    name_part = db.Column(db.String(128))
    name_id = db.Column(db.Integer, db.ForeignKey('name_score.id'))