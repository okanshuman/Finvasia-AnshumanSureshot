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
positions_symbols = set()
purchased_stocks = set()

def process_positions():
    position_response_app = api.get_positions()
    positions = []
    total_invested = 0.0
    total_unrealized = 0.0
    
    # Check if the API response is None or not iterable
    if position_response_app is None:
        return positions, total_invested, total_unrealized
    
    for position in position_response_app:
        if position.get('stat') == 'Ok' and position.get('prd') == 'C':
            position_data = {
                'tsym': position['tsym'],
                'avg_price': float(position['daybuyavgprc']),
                'quantity': int(position['netqty']),
                'invested': float(position['daybuyamt']),
                'unrealized': float(position['urmtom']),
                'daybuyqty': int(position['daybuyqty']),  
                'daysellqty': int(position['daysellqty'])
            }
            positions.append(position_data)
            total_invested += position_data['invested']
            total_unrealized += position_data['unrealized']
    
    return positions, total_invested, total_unrealized

@app.route('/')
def index():
    fetch_stocks(stock_data, positions_symbols)
    positions, total_invested, total_unrealized = process_positions()
    return render_template('index.html', 
                         stocks=stock_data,
                         purchased_stocks=purchased_stocks,
                         positions=positions,
                         total_invested=total_invested,
                         total_unrealized=total_unrealized)

@app.route('/api/positions')
def get_positions():
    try:
        positions, total_invested, total_unrealized = process_positions()
        return jsonify({
            'positions': positions,
            'total_invested': total_invested,
            'total_unrealized': total_unrealized
        })
    except Exception as e:
        logging.error(f"Error fetching positions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stocks')
def get_stocks():
    fetch_stocks(stock_data, positions_symbols)
    return jsonify(stock_data)

@app.route('/api/limits')
def get_limits():
    try:
        # Fetch the response from the API
        limit_response = api.get_limits()
        
        # Calculate available balance
        cash = float(limit_response.get('cash', 0.0))
        marginused = float(limit_response.get('marginused', 0.0))
        brkcollamt = float(limit_response.get('brkcollamt', 0.0))
        payinamt = float(limit_response.get('payin', 0.0))
                
        available_balance = cash - marginused + brkcollamt + payinamt
        
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

scheduler.add_job(func=lambda: sell_holding(api), trigger='interval', seconds=15, id='sell_holding_job') #running selling_holding function every 15 seconds

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=False)