from order_management import *

# Initialize a set to keep track of sold trading symbols
sold_symbols = set()

def sell_holding(api):
    holdings_response = api.get_holdings()
   
    # Check if holdings_response is None or empty
    if holdings_response is None or not isinstance(holdings_response, list):
        print("No valid holdings response received.")
        return
    
    # Extracting the exchange trading symbols and quantities
    for holding in holdings_response:
        if holding['stat'] == 'Ok':
            for tsym_info in holding['exch_tsym']:
                if tsym_info['exch'] == 'NSE':  # Check if the exchange is NSE
                    tradingsymbol = tsym_info['tsym']  # Get the trading symbol for NSE
    
                # Skip if this symbol has already been sold
                if tradingsymbol in sold_symbols:
                    print(f"{tradingsymbol} has already been sold. Skipping.")
                    continue
                
                # Safely get 'npoadqty' from holding, default to 0 if not present
                quantity_str = holding.get('npoadqty', '0')  # Default to '0' if key is missing
                
                # Safely get 'upldprc' (average buy price), default to 0.0 if not present
                averageBuyPrice = float(holding.get('upldprc', 0.0))  # Ensure average buy price is a float

                currentPrice = getCurrentPriceBySymbolName(api, tradingsymbol)  # Fetch current price

                try:
                    quantity = int(quantity_str)  # Convert quantity to integer
                except ValueError:
                    print(f"Invalid quantity '{quantity_str}' for {tradingsymbol}. Skipping.")
                    continue
                
                try:
                    currentPrice = float(currentPrice)  # Convert current price to float
                except ValueError:
                    print(f"Invalid current price '{currentPrice}' for {tradingsymbol}. Skipping.")
                    continue
                
                # Check if current price is greater than or equal to average buy price by 2%
                if currentPrice >= averageBuyPrice * 1.02:  # 2% more than average buy price
                    # Check if quantity is greater than zero before placing an order
                    if quantity > 0:
                        order_response = placeOrder(api, buy_or_sell='S', tradingsymbol=tradingsymbol, quantity=quantity)
                        print(f"Placed sell order for {quantity} of {tradingsymbol}: {order_response}")
                        
                        # Add the symbol to the sold symbols set
                        sold_symbols.add(tradingsymbol)
                    else:
                        print(f"No available quantity to sell for {tradingsymbol}.")
                else:
                    print(f"Current price {currentPrice} is not sufficient to sell {tradingsymbol} (Average Buy Price: {averageBuyPrice}).")
