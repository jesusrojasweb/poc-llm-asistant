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
    is_admin = Column(Boolean, default=False)  # Campo para estatus de administrador
    chats = relationship('Chat', backref='user', lazy='dynamic')
    messages = relationship('ChatMessage', backref='user', lazy='dynamic')

class Chat(db.Model):
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    title = Column(String(100), nullable=True, default='Nuevo Chat')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = relationship('ChatMessage', backref='chat', lazy='dynamic')

class ChatMessage(db.Model):
    id = Column(Integer, primary_key=True)
    content = Column(String(500), nullable=False)
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)
    is_user = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    chat_id = Column(Integer, ForeignKey('chat.id'), nullable=False)
    feedback = Column(Boolean, nullable=True)
    there_is_feedback = Column(Boolean, nullable=True)
