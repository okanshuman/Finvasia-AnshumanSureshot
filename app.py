# app.py
from flask import Flask, render_template, jsonify
from flask_apscheduler import APScheduler
import logging
from fetch_and_buy_stock import fetch_stocks
from order_management import *
import credentials as cr
from sell_holding import sell_holding  # Import the new function

app = Flask(__name__)

# Initialize the scheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

api = ShoonyaApiPy()
api.login(userid=cr.user, password=cr.pwd, twoFA=cr.factor2, vendor_code=cr.vc, api_secret=cr.app_key, imei=cr.imei)

# Global variable to hold stock data
stock_data = []

# Get holdings once and store symbols for filtering later (removing -EQ and -BE)
holdings_response = api.get_holdings()

# Check if holdings_response is valid and not empty
if holdings_response and isinstance(holdings_response, list) and len(holdings_response) > 0:
    holdings_symbols = {holding['tsym'].replace('-EQ', '') for holding in holdings_response[0]['exch_tsym']}
else:
    logging.warning("No valid holdings found.")
    holdings_symbols = set()  # Set to empty if no holdings are found

# Schedule fetch_stocks to run every 1 minute (60 seconds)
scheduler.add_job(func=lambda: fetch_stocks(stock_data, holdings_symbols, api), trigger='interval', seconds=60, id='fetch_stocks_job')

# Schedule sell_holding to run every 15 seconds
scheduler.add_job(func=lambda: sell_holding(api), trigger='interval', seconds=15, id='sell_holding_job')

@app.route('/')
def index():
    fetch_stocks(stock_data, holdings_symbols, api)  # Invoke fetch_stocks whenever the homepage is accessed
    return render_template('index.html', stocks=stock_data)

@app.route('/api/stocks')
def get_stocks():
    """API endpoint to get the latest stocks in JSON format."""
    return jsonify(stock_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)
