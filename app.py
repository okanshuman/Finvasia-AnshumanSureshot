# app.py
from flask import Flask, render_template, jsonify, request
from flask_apscheduler import APScheduler
import logging
from fetch_and_buy_stock import fetch_stocks
from order_management import *
import credentials as cr
import sell_holding
from datetime import datetime, time
import json
import os
from trade_history import update_trade_history_buy, load_trade_history
from utils import ensure_eq_suffix


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

DONT_SELL_FILE = os.path.join(os.path.dirname(__file__), 'dont_sell.json')

def load_dont_sell_list():
    if not os.path.exists(DONT_SELL_FILE):
        return []
    try:
        with open(DONT_SELL_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from {DONT_SELL_FILE}. Returning empty list.")
        return []

def save_dont_sell_list(symbols):
    with open(DONT_SELL_FILE, 'w') as f:
        json.dump(symbols, f)

@app.route('/trades')
def trades():
    return render_template('trades.html')

@app.route('/trades')
def trade_history_page():
    return render_template('trades.html')

@app.route('/api/trade_history')
def get_trade_history():
    return jsonify(load_trade_history())
        
@app.route('/api/dont_sell', methods=['POST'])
def toggle_dont_sell():
    data = request.json
    symbol = data.get('symbol')
    action = data.get('action')
    
    config = load_dont_sell_config()
    dont_sell = config['symbols']
    
    if action == 'add' and symbol not in dont_sell:
        dont_sell.append(symbol)
    elif action == 'remove' and symbol in dont_sell:
        dont_sell.remove(symbol)
        
    config['symbols'] = dont_sell
    save_dont_sell_config(config)
    return jsonify({'status': 'success'})

@app.route('/api/dont_sell')
def get_dont_sell():
    config = load_dont_sell_config()
    return jsonify(config)

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
    config = load_dont_sell_config()
    return render_template('index.html', 
                         stocks=stock_data,
                         purchased_stocks=purchased_stocks,
                         positions=positions,
                         total_invested=total_invested,
                         total_unrealized=total_unrealized,
                         config=config)

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
        quantity = data.get('quantity')

        results = []
        new_purchases = set()

        for stock in stocks_to_buy:
            trading_symbol_name = stock['symbol']
            trading_symbol_name = ensure_eq_suffix(trading_symbol_name)
            correct_symbol_name = getSymbolNameFinvasia(api, trading_symbol_name)

            if quantity:
                qty = quantity
            else:
                current_price = stock['price']
                qty = int(amount / current_price)
                if qty < 1:
                    logging.warning(f"Insufficient funds to buy {stock['symbol']}")
                    continue

            order_response = placeOrder(api, buy_or_sell='B', tradingsymbol=correct_symbol_name, quantity=qty)

            results.append({
                'symbol': stock['symbol'],
                'quantity': qty,
                'order_response': order_response
            })

            new_purchases.add(stock['symbol'])
            
            # Update trade history with the correct qty here
            update_trade_history_buy(
                symbol=stock['symbol'],
                name=stock.get('name', 'Unknown'),
                quantity=qty,
                price=stock['price']
            )
                
        return jsonify({'results': results, 'new_purchases': list(new_purchases)})

    except Exception as e:
        logging.error(f"Error buying stocks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/holdings')
def get_holdings():
    try:
        holdings_response = api.get_holdings()
        #print(holdings_response)
        holdings = []
        
        if holdings_response is None or not isinstance(holdings_response, list):
            return jsonify({'holdings': holdings})

        for holding in holdings_response:
            if holding.get('stat') == 'Ok':
                tradingsymbol = None
                for tsym_info in holding.get('exch_tsym', []):
                    if tsym_info['exch'] == 'NSE':
                        tradingsymbol = tsym_info['tsym']
                        break
                
                if tradingsymbol:
                    tradingsymbol = ensure_eq_suffix(tradingsymbol)
                    stock_name = getSymbolNameFinvasia(api, tradingsymbol)
                    qty = int(holding.get('holdqty', 0))
                    used_qty = int(holding.get('usedqty', 0))
                    avg_price = float(holding.get('upldprc', 0.0))
                    
                    # Skip if quantity equals used quantity
                    if qty == used_qty:
                        continue
                    
                    # Get current price
                    current_price = getCurrentPriceBySymbolName(api, tradingsymbol)
                    current_price = float(current_price) if current_price else avg_price
                                       
                    # Calculate P/L percentages and amounts
                    pl_percent = ((current_price - avg_price) / avg_price * 100) if avg_price else 0
                    invested = avg_price * qty
                    overall_pl_percent = ((current_price * qty - invested) / invested * 100) if invested else 0
                    pl_amount = (current_price - avg_price) * qty
                    overall_pl_amount = (current_price * qty) - invested

                    holdings.append({
                        'symbol': tradingsymbol,
                        'name': stock_name,
                        'quantity': qty,
                        'used_quantity': used_qty,
                        'average_price': avg_price,
                        'current_price': current_price,
                        'pl_percent': pl_percent,
                        'pl_amount': pl_amount,  # Add this line
                        'overall_pl_percent': overall_pl_percent,
                        'overall_pl_amount': overall_pl_amount,  # Add this line
                        'invested': invested
                    })

        return jsonify({'holdings': holdings})
    
    except Exception as e:
        logging.error(f"Error fetching holdings: {e}")
        return jsonify({'error': str(e)}), 500

def should_run_sell_holding():
    """Check if current time is within market hours."""
    now = datetime.now()
    # Market is open on weekdays and between 9:15 AM and 3:30 PM IST
    if now.weekday() < 5:  # Monday to Friday
        market_open_time = time(9, 15)  # 9:15 AM
        market_close_time = time(15, 30)  # 3:30 PM
        return market_open_time <= now.time() <= market_close_time
    return False

@scheduler.task('interval', id='sell_holding_job', seconds=15)
def scheduled_sell_holding():
    if should_run_sell_holding():
        sell_holding.sell_holding(api)
    else:
        print("Market is closed. sell_holding will not run.")

@app.route('/api/sell_percentage', methods=['POST'])
def update_sell_percentage():
    data = request.json
    percentage = float(data.get('percentage', 2.0))
    
    config = load_dont_sell_config()
    config['sell_percentage'] = percentage
    save_dont_sell_config(config)
    return jsonify({'status': 'success', 'new_percentage': percentage})

def load_dont_sell_config():
    if not os.path.exists(DONT_SELL_FILE):
        return {'symbols': [], 'sell_percentage': 2.0}
    try:
        with open(DONT_SELL_FILE, 'r') as f:
            config = json.load(f)
            # Handle legacy format
            if isinstance(config, list):
                return {'symbols': config, 'sell_percentage': 2.0}
            return config
    except json.JSONDecodeError:
        return {'symbols': [], 'sell_percentage': 2.0}

def save_dont_sell_config(config):
    with open(DONT_SELL_FILE, 'w') as f:
        json.dump(config, f)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=False)