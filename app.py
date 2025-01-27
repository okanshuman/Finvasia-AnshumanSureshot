from flask import Flask, render_template, jsonify, request
from flask_apscheduler import APScheduler
import logging
from fetch_and_buy_stock import fetch_stocks
from order_management import *
import credentials as cr
from sell_holding import sell_holding
from datetime import datetime, time

app = Flask(__name__)

# Initialize the scheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

api = ShoonyaApiPy()
api.login(userid=cr.user, password=cr.pwd, twoFA=cr.factor2, 
          vendor_code=cr.vc, api_secret=cr.app_key, imei=cr.imei)

stock_data = []
holdings_symbols = set()
purchased_stocks = set()

position_response_app = api.get_positions()
print(position_response_app)

def should_run_sell_holding():
    """Check if current time is within market hours."""
    now = datetime.now()
    if now.weekday() < 5:  # Monday to Friday
        market_open_time = time(9, 15)
        market_close_time = time(15, 30)
        return market_open_time <= now.time() <= market_close_time
    return False

@scheduler.task('interval', id='sell_holding_job', seconds=15)
def scheduled_sell_holding():
    if should_run_sell_holding():
        sell_holding(api)
    else:
        print("Market is closed. sell_holding will not run.")

@app.route('/')
def index():
    fetch_stocks(stock_data, holdings_symbols)
    return render_template('index.html', 
                         stocks=stock_data,
                         purchased_stocks=purchased_stocks)

@app.route('/api/stocks')
def get_stocks():
    return jsonify(stock_data)

@app.route('/api/limits')
def get_limits():
    try:
        # Fetch the response from the API
        limit_response = api.get_limits()
        print(limit_response)
        
        # Calculate available balance
        cash = float(limit_response.get('cash', 0.0))
        marginused = float(limit_response.get('marginused', 0.0))
        brkcollamt = float(limit_response.get('brkcollamt', 0.0))
        
        available_balance = cash - marginused + brkcollamt
        
        # Return the available balance as "cash"
        return jsonify({'cash': available_balance})
    except Exception as e:
        logging.error(f"Error fetching limits: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/buy_stocks', methods=['POST'])
def buy_stocks():
    try:
        data = request.json
        stocks_to_buy = data.get('stocks', [])
        amount = data.get('amount', 5000)
        
        if not isinstance(amount, (int, float)) or amount < 1000:
            return jsonify({'error': 'Invalid investment amount (minimum ₹1000)'}), 400

        results = []
        new_purchases = set()

        for stock in stocks_to_buy:
            trading_symbol_name = stock['symbol']
            correct_symbol_name = getSymbolNameFinvasia(api, trading_symbol_name)
            current_price = stock['price']
            quantity = int(amount / current_price)

            if quantity < 1:
                continue  # Skip stocks where quantity would be zero

            order_response = placeOrder(api, buy_or_sell='B', 
                                      tradingsymbol=correct_symbol_name, 
                                      quantity=quantity)
            
            results.append({
                'symbol': stock['symbol'],
                'quantity': quantity,
                'order_response': order_response
            })
            
            new_purchases.add(stock['symbol'])

        # Update purchased stocks
        global purchased_stocks
        purchased_stocks.update(new_purchases)

        return jsonify({
            'message': f'Successfully placed orders for {len(results)} stocks',
            'results': results
        }), 200

    except Exception as e:
        logging.error(f"Error buying stocks: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)