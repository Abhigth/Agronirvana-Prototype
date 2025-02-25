from flask import Flask, render_template, request
import requests
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime, timedelta
import random
from flask import redirect, url_for, flash
from werkzeug.security import generate_password_hash
import pickle
import numpy as np
from flask_mail import Mail, Message
from flask_babel import Babel, gettext as _




# Load the trained risk model
with open("risk_model.pkl", "rb") as f:
    risk_model = pickle.load(f)


basedir = os.path.abspath(os.path.dirname(__file__))



app = Flask(__name__)
app.secret_key = 'Agronv25'  # Replace with a unique, secure key
# Configure the SQLite database (for simplicity)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'new_agronirvana.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure Flask-Mail settings (for prototype/testing)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'test.agronirvana@gmail.com'       # Replace with your test email
app.config['MAIL_PASSWORD'] = 'ieraqkqlsbnqamvb'          # Replace with your test email's password
# Initialize the Mail instance
mail = Mail(app)

# Configure Babel
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'hi', 'te', 'kn']  # English, Hindi, Telugu, Kannada (for example)
babel = Babel(app)

# Do not create a new instance; import the shared one instead.
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from models import db, RiskAssessment, User, Policy, Feedback, Claim  # Import User along with RiskAssessment

# Initialize the shared SQLAlchemy instance (if not already done)
db.init_app(app)

# Set up Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect to 'login' route for unauthorized access

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
    nasa_api_key = "untLag6VYP4yBoASPLVOXrfdVyuYq8E6WtS66t6Q"  # Replace with your NASA API key
    # NASA Earth API endpoint
    url = f"https://api.nasa.gov/planetary/earth/assets?lon={lon}&lat={lat}&date={date}&dim=0.15&api_key={nasa_api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # Check if the API returns a URL for the satellite image
        if "url" in data:
            return data["url"]
    return None


def get_ndvi(lat, lon):
    """
    Simulate NDVI value retrieval for the given coordinates.
    In a real implementation, this function would process satellite imagery
    to compute the NDVI value. Here, we return a random value between 0.2 and 0.8.
    """
    return round(random.uniform(0.2, 0.8), 2)

def assess_risk(weather_data, ndvi):
    """
    Compute a risk score based on weather data and NDVI.
    The function returns a risk level as a string.
    """
    risk_score = 0

    # Extract weather details
    temp = weather_data.get('main', {}).get('temp', None)
    humidity = weather_data.get('main', {}).get('humidity', None)
    
    if temp is not None:
        # Example: For every degree above 35°C, add 1 point to risk.
        if temp > 35:
            risk_score += (temp - 35)
    
    if humidity is not None:
        # Example: For humidity below 40%, add points for each percent below 40.
        if humidity < 40:
            risk_score += (40 - humidity)
    
    # Factor in NDVI (lower NDVI means higher risk)
    if ndvi < 0.3:
        risk_score += 10  # High risk added
    elif ndvi < 0.5:
        risk_score += 5   # Moderate risk added
    else:
        risk_score -= 2   # Good vegetation can slightly reduce risk

    # Map the numerical risk_score to a risk level label
    if risk_score > 15:
        return "High Risk"
    elif risk_score > 5:
        return "Moderate Risk"
    else:
        return "Low Risk"
    

def assess_risk_advanced(weather_data, ndvi):
    # Extract features: temperature, humidity, and NDVI
    temp = weather_data.get('main', {}).get('temp', 0)
    humidity = weather_data.get('main', {}).get('humidity', 0)
    
    # Create a features array; shape must be (1, 3)
    features = np.array([[temp, humidity, ndvi]])
    
    # Use the model to predict risk; 1 indicates High Risk, 0 indicates Low/Moderate Risk
    prediction = risk_model.predict(features)
    
    if prediction[0] == 1:
        return "High Risk"
    else:
        return "Low/Moderate Risk"




# (Assuming get_weather_data, get_ndvi, and assess_risk are defined above)

@app.route('/', methods=['GET', 'POST'])
def index():
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
            risk_level = assess_risk_advanced(weather_data, ndvi)  # Use the advanced model function
            risk_level = risk_level.strip().title()  # Normalize the string (e.g., "high risk" becomes "High Risk")
    
    # Log the risk assessment record to the database
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
                from models import Claim
                new_claim = Claim(risk_assessment_id=new_record.id)
                db.session.add(new_claim)
                db.session.commit()

                msg = Message("High Risk Alert - Claim Created",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[current_user.email])
                msg.body = f"Dear {current_user.username},\n\nA high-risk assessment has been detected for your farm and a claim has been automatically created. Our team will review it shortly.\n\nThank you,\nAgroNirvana Team"
                mail.send(msg)

        else:
            weather_data = {"error": "Unable to fetch weather data."}
        
        default_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        satellite_url = get_satellite_image(lat, lon, default_date)
    
    return render_template('index.html', weather=weather_data, risk=risk_level, satellite_url=satellite_url, ndvi=ndvi)



@app.route('/dashboard')
@login_required
def dashboard():
    records = RiskAssessment.query.order_by(RiskAssessment.timestamp.desc()).all()
    return render_template('dashboard.html', records=records)



from flask import redirect, url_for, flash
from werkzeug.security import generate_password_hash

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if username or email already exists
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists.")
            return redirect(url_for('register'))

        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please log in.")
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Logged in successfully.")
            return redirect(url_for('dashboard'))  # Or wherever you want to redirect after login
        else:
            flash("Invalid username or password.")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for('index'))

@app.route('/claims')
def claims():
    # Query all claims, ordered by most recent
    from models import Claim  # Ensure Claim is imported
    claim_records = Claim.query.order_by(Claim.timestamp.desc()).all()
    return render_template('claims.html', claims=claim_records)

@app.route('/policies')
@login_required  # Only authenticated users can view their policies
def policies():
    # Retrieve policies associated with the current user
    user_policies = current_user.policies
    return render_template('policies.html', policies=user_policies)


@app.route('/purchase_policy', methods=['GET', 'POST'])
@login_required
def purchase_policy():
    if request.method == 'POST':
        # Retrieve form data for policy purchase
        coverage_amount = float(request.form.get('coverage_amount'))
        premium = float(request.form.get('premium'))
        effective_date = datetime.strptime(request.form.get('effective_date'), '%Y-%m-%d')
        expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d')
        
        # For simplicity, generate a policy number (in a real app, use a better method)
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
        # Simulate a successful payment
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
        # Retrieve form data
        rating = request.form.get('rating')
        comments = request.form.get('comments')
        
        # Validate that comments are provided and not just whitespace
        if not comments or comments.strip() == "":
            flash("Comments cannot be empty!")
            return redirect(url_for('feedback'))
        
        # Attempt to convert the rating to an integer; if not provided or invalid, set to None
        try:
            rating = int(rating)
        except (ValueError, TypeError):
            rating = None

        # Create and save a new feedback record
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
    total_claims = Claim.query.count()  # Ensure Claim is imported
    total_policies = Policy.query.count()  # If you have Policy implemented
    return render_template('analytics.html', 
                           total_assessments=total_assessments,
                           total_claims=total_claims,
                           total_policies=total_policies)


@app.route('/feedback_analytics')
@login_required
def feedback_analytics():
    # Query all feedback entries, ordered by the most recent
    from models import Feedback  # Ensure Feedback is imported from models.py
    feedbacks = Feedback.query.order_by(Feedback.timestamp.desc()).all()
    return render_template('feedback_analytics.html', feedbacks=feedbacks)


@app.route('/check_data')
def check_data():
    from models import HistoricalWeather  # Ensure the model is imported
    count = HistoricalWeather.query.count()
    return f"HistoricalWeather table has {count} records."



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)