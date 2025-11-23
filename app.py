from flask import Flask, render_template, request, redirect, url_for, flash
import requests
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime, timedelta
import random
from werkzeug.security import generate_password_hash
import pickle
import numpy as np
from flask_mail import Mail, Message
from flask_babel import Babel, gettext as _

# Flask-Login imports
from flask_login import LoginManager, login_user, logout_user, current_user, login_required

# Load the trained risk model
with open("risk_model.pkl", "rb") as f:
    risk_model = pickle.load(f)

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.secret_key = 'Agronv25'  # Replace with a unique, secure key

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'new_agronirvana.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure Flask-Mail settings (for prototype/testing)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'test.agronirvana@gmail.com'
app.config['MAIL_PASSWORD'] = 'ieraqkqlsbnqamvb'
mail = Mail(app)

# Configure Babel
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'hi', 'te', 'kn']
babel = Babel(app)

# Initialize the shared SQLAlchemy instance
from models import db, RiskAssessment, User, Policy, Feedback, Claim
db.init_app(app)

# Set up Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect to /login for unauthorized users

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Replace with your actual OpenWeatherMap API key
WEATHER_API_KEY = '3401fdee3f9be8b96b31e1b7a84ec192'

def get_weather_data(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    print(response.status_code, response.text)  # Debug line
    if response.status_code == 200:
        return response.json()
    else:
        return None

def get_satellite_image(lat, lon, date):
    nasa_api_key = "untLag6VYP4yBoASPLVOXrfdVyuYq8E6WtS66t6Q"
    url = f"https://api.nasa.gov/planetary/earth/assets?lon={lon}&lat={lat}&date={date}&dim=0.15&api_key={nasa_api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if "url" in data:
            return data["url"]
    return None

def get_ndvi(lat, lon):
    return round(random.uniform(0.2, 0.8), 2)

def assess_risk_advanced(weather_data, ndvi):
    temp = weather_data.get('main', {}).get('temp', 0)
    humidity = weather_data.get('main', {}).get('humidity', 0)
    features = np.array([[temp, humidity, ndvi]])
    prediction = risk_model.predict(features)
    if prediction[0] == 1:
        return "High Risk"
    else:
        return "Low/Moderate Risk"

# ------------------------------
# 1) NEW HOME ROUTE
# ------------------------------
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('analysis'))
    return render_template('home.html')  # Minimal page with login/register links

# ------------------------------
# 2) RENAMED INDEX -> ANALYSIS
#    Protected by @login_required
# ------------------------------
@app.route('/analysis', methods=['GET', 'POST'])
@login_required
def analysis():
    weather_data = None
    risk_level = "Not Assessed"
    satellite_url = None  
    ndvi = None  

    if request.method == 'POST':
        lat = request.form.get('latitude')
        lon = request.form.get('longitude')
        weather_data = get_weather_data(lat, lon)
        
        if weather_data:
            ndvi = get_ndvi(lat, lon)
            risk_level = assess_risk_advanced(weather_data, ndvi).strip().title()
    
            new_record = RiskAssessment(
                latitude=lat,
                longitude=lon,
                temperature=weather_data['main']['temp'],
                humidity=weather_data['main']['humidity'],
                ndvi=ndvi,
                risk_level=risk_level
            )
            db.session.add(new_record)
            db.session.commit()

            if risk_level == "High Risk":
                new_claim = Claim(risk_assessment_id=new_record.id)
                db.session.add(new_claim)
                db.session.commit()

                msg = Message("High Risk Alert - Claim Created",
                              sender=app.config['MAIL_USERNAME'],
                              recipients=[current_user.email])
                msg.body = (
                    f"Dear {current_user.username},\n\n"
                    "A high-risk assessment has been detected for your farm and a claim "
                    "has been automatically created. Our team will review it shortly.\n\n"
                    "Thank you,\nAgroNirvana Team"
                )
                mail.send(msg)
        else:
            weather_data = {"error": "Unable to fetch weather data."}
        
        default_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        satellite_url = get_satellite_image(lat, lon, default_date)
    
    return render_template('analysis.html', weather=weather_data, risk=risk_level, satellite_url=satellite_url, ndvi=ndvi)

@app.route('/dashboard')
@login_required
def dashboard():
    records = RiskAssessment.query.order_by(RiskAssessment.timestamp.desc()).all()
    return render_template('dashboard.html', records=records)

# ------------------------------
# Authentication Routes
# ------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('analysis'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists.")
            return redirect(url_for('register'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please log in.")
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('analysis'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Logged in successfully.")
            return redirect(url_for('analysis'))
        else:
            flash("Invalid username or password.")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for('home'))

# ------------------------------
# Additional Routes
# ------------------------------
@app.route('/claims')
def claims():
    claim_records = Claim.query.order_by(Claim.timestamp.desc()).all()
    return render_template('claims.html', claims=claim_records)

@app.route('/policies')
@login_required
def policies():
    user_policies = current_user.policies
    return render_template('policies.html', policies=user_policies)

@app.route('/purchase_policy', methods=['GET', 'POST'])
@login_required
def purchase_policy():
    if request.method == 'POST':
        coverage_amount = float(request.form.get('coverage_amount'))
        premium = float(request.form.get('premium'))
        effective_date = datetime.strptime(request.form.get('effective_date'), '%Y-%m-%d')
        expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d')
        
        policy_number = "POL" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
        
        new_policy = Policy(
            user_id=current_user.id,
            policy_number=policy_number,
            coverage_amount=coverage_amount,
            premium=premium,
            effective_date=effective_date,
            expiry_date=expiry_date,
            status='Active'
        )
        db.session.add(new_policy)
        db.session.commit()
        flash("Policy purchased successfully!")
        return redirect(url_for('policies'))
    return render_template('purchase_policy.html')

@app.route('/dummy_pay', methods=['GET', 'POST'])
@login_required
def dummy_pay():
    if request.method == 'POST':
        flash("Payment simulated successfully!")
        return redirect(url_for('payment_success'))
    return render_template('dummy_pay.html')

@app.route('/payment_success', methods=['GET', 'POST'])
@login_required
def payment_success():
    flash("Your payment was successful! Your policy has been activated.")
    return redirect(url_for('policies'))

@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        rating = request.form.get('rating')
        comments = request.form.get('comments')
        
        if not comments or comments.strip() == "":
            flash("Comments cannot be empty!")
            return redirect(url_for('feedback'))
        
        try:
            rating = int(rating)
        except (ValueError, TypeError):
            rating = None

        new_feedback = Feedback(user_id=current_user.id, rating=rating, comments=comments.strip())
        db.session.add(new_feedback)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while saving your feedback.")
            print("Error committing feedback:", e)
            return redirect(url_for('feedback'))
        
        flash("Thank you for your feedback!")
        return redirect(url_for('dashboard'))
    
    return render_template('feedback.html')

@app.route('/analytics')
@login_required
def analytics():
    total_assessments = RiskAssessment.query.count()
    total_claims = Claim.query.count()
    total_policies = Policy.query.count()
    return render_template('analytics.html', 
                           total_assessments=total_assessments,
                           total_claims=total_claims,
                           total_policies=total_policies)

@app.route('/feedback_analytics')
@login_required
def feedback_analytics():
    feedbacks = Feedback.query.order_by(Feedback.timestamp.desc()).all()
    return render_template('feedback_analytics.html', feedbacks=feedbacks)

@app.route('/check_data')
def check_data():
    from models import HistoricalWeather
    count = HistoricalWeather.query.count()
    return f"HistoricalWeather table has {count} records."

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
