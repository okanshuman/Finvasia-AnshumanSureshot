# app.py
from flask import Flask, render_template, jsonify, request
from flask_apscheduler import APScheduler
import logging
from fetch_and_buy_stock import fetch_stocks
from order_management import *
import credentials as cr
from sell_holding import sell_holding

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

# Load purchased stocks from persistent storage (you might want to use a database in production)
purchased_stocks = set()

# Schedule sell_holding to run every 15 seconds
scheduler.add_job(func=lambda: sell_holding(api), trigger='interval', seconds=15, id='sell_holding_job')


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
        limit_response = api.get_limits()
        return jsonify({'cash': limit_response['cash']})
    except Exception as e:
        logging.error(f"Error fetching limits: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/buy_stocks', methods=['POST'])
def buy_stocks():
    try:
        stocks_to_buy = request.json
        results = []
        new_purchases = set()

        for stock in stocks_to_buy:
            trading_symbol_name = stock['symbol']
            correct_symbol_name = getSymbolNameFinvasia(api, trading_symbol_name)
            current_price = stock['price']
            quantity = int(5000 / current_price)

            order_response = placeOrder(api, buy_or_sell='B', 
                                      tradingsymbol=correct_symbol_name, 
                                      quantity=quantity)
            
            results.append({
                'symbol': stock['symbol'],
                'quantity': quantity,
                'order_response': order_response
            })
            
            # Add to purchased stocks
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