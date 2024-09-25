from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128))
    is_admin = Column(Boolean, default=False)  # New field for admin status
    messages = relationship('ChatMessage', backref='user', lazy='dynamic')

class ChatMessage(db.Model):
    id = Column(Integer, primary_key=True)
    content = Column(String(500))
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)
    is_user = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    feedback = Column(Boolean, nullable=True)
    there_is_feedback = Column(Boolean, nullable=True)
