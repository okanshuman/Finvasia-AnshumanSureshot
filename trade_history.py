import json
import os
from datetime import datetime

TRADE_HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'trade_history.json')

def load_trade_history():
    try:
        if not os.path.exists(TRADE_HISTORY_FILE):
            return []
        with open(TRADE_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_trade_history(history):
    try:
        with open(TRADE_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except IOError as e:
        print(f"Error saving trade history: {e}")

def update_trade_history_buy(symbol, name, quantity, price):
    history = load_trade_history()
    now = datetime.now().isoformat()
    
    existing = next((item for item in history if item['symbol'] == symbol), None)
    
    if existing:
        # Update existing entry
        total_quantity = existing['total_quantity'] + quantity
        new_avg = ((existing['buy_price_avg'] * existing['total_quantity']) + (price * quantity)) / total_quantity
        existing.update({
            'total_quantity': total_quantity,
            'buy_price_avg': round(new_avg, 2),
            'sell_price': None,
            'sell_date': None
        })
    else:
        # Add new entry
        history.append({
            'symbol': symbol,
            'name': name,
            'total_quantity': quantity,
            'buy_price_avg': price,
            'buy_date': now,
            'sell_price': None,
            'sell_date': None
        })
    
    save_trade_history(history)

def update_trade_history_sell(symbol, sell_price):
    history = load_trade_history()
    now = datetime.now().isoformat()
    
    for entry in history:
        if entry['symbol'] == symbol and not entry['sell_price']:
            entry.update({
                'sell_price': sell_price,
                'sell_date': now
            })
            save_trade_history(history)
            break