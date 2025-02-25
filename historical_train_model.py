import numpy as np
import pickle
from sklearn.linear_model import LogisticRegression
from app import app, db
from models import HistoricalWeather

def label_record(record):
    # For example, label high risk as: Temperature > 38°C and Humidity < 40%
    if record.temperature > 38 and record.humidity < 40:
        return 1
    return 0

with app.app_context():
    # Retrieve historical weather data
    records = HistoricalWeather.query.all()
    if not records:
        print("No historical data found. Please run your data collector first.")
    else:
        X = []
        y = []
        for rec in records:
            X.append([rec.temperature, rec.humidity])
            y.append(label_record(rec))
        X = np.array(X)
        y = np.array(y)
        
        # Train the model using historical data
        model = LogisticRegression()
        model.fit(X, y)
        
        print("Historical training accuracy:", model.score(X, y))
        
        # Save the trained model
        with open("risk_model_historical.pkl", "wb") as f:
            pickle.dump(model, f)
        
        print("Historical data model trained and saved as risk_model_historical.pkl!")
