# sell_holding
from order_management import *
from app import load_dont_sell_list
from trade_history import update_trade_history_sell
from app import load_dont_sell_config


# Initialize a set to keep track of sold trading symbols
sold_symbols = set()

def sell_holding(api):
    config = load_dont_sell_config()
    dont_sell_symbols = config['symbols']
    sell_percentage = config.get('sell_percentage', 2.0)  # Default to 2% if missing
    
    holdings_response = api.get_holdings()
    
    if holdings_response is None or not isinstance(holdings_response, list):
        return

    for holding in holdings_response:
        try:
            if holding['stat'] == 'Ok':
                # First check if both holdqty and usedqty exist and get their values
                holdqty = int(holding.get('holdqty', '0'))
                usedqty = int(holding.get('usedqty', '0'))
                
                # Skip this holding if either:
                # 1. holdqty is zero (no holdings) or
                # 2. usedqty is non-zero (already being used in some order)
                if holdqty == 0 or usedqty > 0:
                    continue
                
                # Extract trading symbol
                tradingsymbol = None
                for tsym_info in holding.get('exch_tsym', []):
                    if tsym_info['exch'] == 'NSE':
                        tradingsymbol = tsym_info['tsym']
                        break

                if not tradingsymbol:
                    continue
                
                if tradingsymbol in dont_sell_symbols:
                    print(f"Skipping {tradingsymbol} (marked as don't sell)")
                    continue

                # Skip if this symbol has already been sold
                if tradingsymbol in sold_symbols:
                    #print(f"{tradingsymbol} has already been sold. Skipping.")
                    continue
                
                # Use holdqty as the quantity to sell
                quantity = holdqty
                #print(f"Available quantity for {tradingsymbol}: {quantity} (holdqty: {holdqty}, usedqty: {usedqty})")
                
                # Safely get 'upldprc' (average buy price), default to 0.0 if not present
                try:
                    averageBuyPrice = float(holding.get('upldprc', 0.0))
                    #print(f"Average buy price for {tradingsymbol}: {averageBuyPrice}")
                except ValueError:
                    print(f"Invalid average buy price for {tradingsymbol}. Skipping.")
                    continue
                
                # Get current price
                try:
                    currentPrice = getCurrentPriceBySymbolName(api, tradingsymbol)
                    currentPrice = float(currentPrice)
                    #print(f"Current price for {tradingsymbol}: {currentPrice}")
                except (ValueError, TypeError):
                    print(f"Invalid current price for {tradingsymbol}. Skipping.")
                    continue
                
                # Proceed with sell logic only if we have valid prices
                if currentPrice <= 0:
                    print(f"Invalid current price (0 or negative) for {tradingsymbol}.")
                    continue
                    
                if averageBuyPrice <= 0:
                    print(f"Invalid average buy price (0 or negative) for {tradingsymbol}.")
                    continue
                
                # Check if current price is greater than or equal to average buy price by 2%
                if currentPrice >= averageBuyPrice * (1 + sell_percentage/100):
                    try:
                        order_response = placeOrder(api, buy_or_sell='S',tradingsymbol=tradingsymbol,quantity=quantity)
                        print(f"Placed sell order for {quantity} of {tradingsymbol}: {order_response}")
                        
                        # Add the symbol to the sold symbols set only if order was successful
                        if order_response and isinstance(order_response, dict) and order_response.get('stat') == 'Ok':
                            sold_symbols.add(tradingsymbol)
                            update_trade_history_sell(tradingsymbol, currentPrice)
                        else:
                            print(f"Order placement failed for {tradingsymbol}")
                            
                    except Exception as e:
                        print(f"Error placing order for {tradingsymbol}: {str(e)}")
                else:
                    print(f"Current price {currentPrice} is not sufficient to sell {tradingsymbol} "
                          f"(Average Buy Price: {averageBuyPrice}, Required: {averageBuyPrice * 1.02})")
                          
        except Exception as e:
            print(f"Error processing holding: {str(e)}")
            continue
