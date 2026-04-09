from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # Сделал nullable
    password_hash = db.Column(db.String(256), nullable=False)
    city = db.Column(db.String(100))
    bio = db.Column(db.Text)
    avatar = db.Column(db.String(500))
    age = db.Column(db.Integer, default=18)  # Добавлено
    interests = db.Column(db.Text)  # Добавлено
    is_premium = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)  # Добавлено
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Отношения
    parties = db.relationship('Party', backref='organizer', lazy=True, foreign_keys='Party.organizer_id')
    tickets = db.relationship('Ticket', backref='buyer', lazy=True, foreign_keys='Ticket.buyer_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Party(db.Model):
    """Модель вечеринки"""
    __tablename__ = 'parties'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    city = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(300))
    genre = db.Column(db.String(100))
    theme = db.Column(db.String(100))  # Добавлено
    date = db.Column(db.DateTime, nullable=False)
    ticket_price = db.Column(db.Float, nullable=False)  # Float для совместимости с float в app.py
    min_age = db.Column(db.Integer, default=18)
    photo_url = db.Column(db.String(500))
    image = db.Column(db.String(500))
    total_tickets = db.Column(db.Integer, default=100)  # Добавлено
    available_tickets = db.Column(db.Integer, default=100)  # Добавлено
    is_hot = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Внешние ключи
    organizer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Отношения
    tickets = db.relationship('Ticket', backref='party', lazy=True)
    reviews = db.relationship('Review', backref='party', lazy=True)
    
    @property
    def price(self):
        return self.ticket_price
    
    def __repr__(self):
        return f'<Party {self.title}>'


class Ticket(db.Model):
    """Модель билета"""
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float)  # Добавлено
    status = db.Column(db.String(20), default='active')
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    qr_code = db.Column(db.String(500))
    
    # Внешние ключи
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # изменено с user_id
    party_id = db.Column(db.Integer, db.ForeignKey('parties.id'), nullable=False)
    
    @property
    def party_title(self):
        return self.party.title if self.party else 'Неизвестно'
    
    @property
    def date(self):
        return self.party.date if self.party else None
    
    def __repr__(self):
        return f'<Ticket {self.id}>'


class Review(db.Model):
    """Модель отзыва"""
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Внешние ключи
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    party_id = db.Column(db.Integer, db.ForeignKey('parties.id'), nullable=False)
    
    # Отношения
    user = db.relationship('User', backref='reviews')
    
    def __repr__(self):
        return f'<Review {self.id} - {self.rating}★>'


class Message(db.Model):
    """Модель сообщения"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)  # изменено с content
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # изменено с created_at
    is_read = db.Column(db.Boolean, default=False)
    party_id = db.Column(db.Integer, db.ForeignKey('parties.id'), nullable=True)  # Добавлено
    
    # Внешние ключи
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Отношения
    from_user = db.relationship('User', foreign_keys=[from_user_id], backref='sent_messages')
    to_user = db.relationship('User', foreign_keys=[to_user_id], backref='received_messages')
    
    def __repr__(self):
        return f'<Message {self.id}>'