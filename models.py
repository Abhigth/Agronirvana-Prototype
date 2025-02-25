from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Policy(db.Model):
    __tablename__ = 'policy'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    policy_number = db.Column(db.String(100), unique=True, nullable=False)
    coverage_amount = db.Column(db.Float, nullable=False)
    premium = db.Column(db.Float, nullable=False)
    effective_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='Active')  # Active, Expired, Cancelled

    def __repr__(self):
        return f'<Policy {self.policy_number} - {self.status}>'
    


class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    rating = db.Column(db.Integer, nullable=True)  # e.g., 1 to 5
    comments = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Feedback {self.id} - Rating: {self.rating}>'

    

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    registered_on = db.Column(db.DateTime, default=datetime.utcnow)
     # Relationship to policies
    policies = db.relationship('Policy', backref='owner', lazy=True)
    # Relationship to claims
    claims = db.relationship('Claim', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class RiskAssessment(db.Model):
    __tablename__ = 'risk_assessment'
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.String(50))
    longitude = db.Column(db.String(50))
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    ndvi = db.Column(db.Float)
    risk_level = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # Relationship to claim (one-to-one, for example)
    claim = db.relationship('Claim', backref='risk_assessment', uselist=False)

    def __repr__(self):
        return f'<RiskAssessment {self.id} - {self.risk_level}>'


class HistoricalWeather(db.Model):
    __tablename__ = 'historical_weather'
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<HistoricalWeather {self.id}: {self.temperature}°C, {self.humidity}% at {self.timestamp}>'

# New Claim model to store insurance claims
class Claim(db.Model):
    __tablename__ = 'claim'
    id = db.Column(db.Integer, primary_key=True)
    risk_assessment_id = db.Column(db.Integer, db.ForeignKey('risk_assessment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    claim_status = db.Column(db.String(50), default='Pending')  # Pending, Approved, Rejected
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Claim {self.id} - Status: {self.claim_status}>'
