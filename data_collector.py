from apscheduler.schedulers.background import BackgroundScheduler
import requests
from datetime import datetime
from app import app, db
from models import HistoricalWeather


WEATHER_API_KEY = '3401fdee3f9be8b96b31e1b7a84ec192'
LAT = 19.067
LON = 76.908

def fetch_and_store_weather():
    with app.app_context():
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            temperature = data['main']['temp']
            humidity = data['main']['humidity']
            record = HistoricalWeather(
                latitude=LAT,
                longitude=LON,
                temperature=temperature,
                humidity=humidity,
                timestamp=datetime.utcnow()
            )
            db.session.add(record)
            db.session.commit()
            print(f"Stored weather data: {temperature}°C, {humidity}% at {datetime.utcnow()}")
        else:
            print("Failed to fetch weather data:", response.status_code, response.text)

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_store_weather, 'interval', minutes=20)  # Runs every half-hour
    scheduler.start()
    
    try:
        while True:
            pass  # Keep the script running
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
