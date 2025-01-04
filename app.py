# app.py

from flask import Flask, render_template, jsonify
from flask_apscheduler import APScheduler
import logging

# Import the fetch_stocks function from stock_fetcher module
from stock_fetcher import fetch_stocks

app = Flask(__name__)

# Initialize the scheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# Global variable to hold stock data
stock_data = []

# Schedule fetch_stocks to run every 5 minutes (300 seconds) with a unique ID
scheduler.add_job(func=lambda: fetch_stocks(stock_data), trigger='interval', seconds=300, id='fetch_stocks_job')

@app.route('/')
def index():
    fetch_stocks(stock_data)  # Invoke fetch_stocks whenever the homepage is accessed
    return render_template('index.html', stocks=stock_data)

@app.route('/api/stocks')
def get_stocks():
    """API endpoint to get the latest stocks in JSON format."""
    return jsonify(stock_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)
