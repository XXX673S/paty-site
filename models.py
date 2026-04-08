from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    city = db.Column(db.String(50))
    age = db.Column(db.Integer)
    avatar = db.Column(db.String(200), default='default.png')
    bio = db.Column(db.Text, default='')
    interests = db.Column(db.String(200), default='')
    is_premium = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Party(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    city = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(200))
    date = db.Column(db.DateTime, nullable=False)
    min_age = db.Column(db.Integer, default=0)
    theme = db.Column(db.String(100))
    genre = db.Column(db.String(50))
    photo_url = db.Column(db.String(200))
    ticket_price = db.Column(db.Float, default=0)
    total_tickets = db.Column(db.Integer)
    available_tickets = db.Column(db.Integer)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    organizer = db.relationship('User', backref='parties')

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    party_id = db.Column(db.Integer, db.ForeignKey('party.id'))
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    price = db.Column(db.Float)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    party = db.relationship('Party', backref='tickets')
    buyer = db.relationship('User', backref='tickets')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    party_id = db.Column(db.Integer, db.ForeignKey('party.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    party = db.relationship('Party', backref='reviews')
    user = db.relationship('User', backref='reviews')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    party_id = db.Column(db.Integer, db.ForeignKey('party.id'))
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    party = db.relationship('Party', backref='messages')
    from_user = db.relationship('User', foreign_keys=[from_user_id])
    to_user = db.relationship('User', foreign_keys=[to_user_id])