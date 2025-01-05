# fetch_and_buy_stock.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
from datetime import datetime
import pytz  # Import pytz for timezone handling
from utils import round_to_two_decimal, is_valid_symbol, clean_symbol
from order_management import placeOrder, getSymbolNameFinvasia  # Import getSymbolNameFinvasia

# Global set to keep track of ordered symbols
ordered_symbols = set()

def fetch_stocks(stock_data, holdings, api):
    urls = [
        "https://chartink.com/screener/anshuman-sureshot1",
        "https://chartink.com/screener/anshuman-sureshot2",
        "https://chartink.com/screener/anshuman-sureshot3"
    ]

    chrome_options = Options()
    chrome_options.add_argument("--headless")  
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=ChromeService(executable_path='/usr/bin/chromedriver'), options=chrome_options)
    new_stocks = []

    try:
        for url in urls:
            logging.info(f"Fetching stocks from {url}")
            driver.get(url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'table-striped')))
            stock_list = driver.find_element(By.CLASS_NAME, 'table-striped')
            rows = stock_list.find_elements(By.TAG_NAME, 'tr')[1:]  

            #print(f"Found {len(rows)} rows of stock data from {url}.")

            for row in rows:
                columns = row.find_elements(By.TAG_NAME, 'td')
                if len(columns) > 5:  # Ensure there are enough columns to avoid index errors
                    stock_name = columns[1].text.strip()
                    stock_symbol = clean_symbol(columns[2].text.strip().replace('$', '').replace('-EQ', ''))  # Remove -EQ
                    current_price = round_to_two_decimal(float(columns[5].text.strip()))  # Fetch current price
                    identified_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Check if the stock is valid and not already in the list and not in holdings
                    if is_valid_symbol(stock_symbol) and stock_symbol not in holdings:
                        new_stocks.append({"name": stock_name, 
                                           "symbol": stock_symbol, 
                                           "current_price": current_price, 
                                           "date": identified_date})

        # Create a set of existing symbols for quick lookup
        existing_symbols = {stock['symbol'] for stock in stock_data}

        # Remove stocks that are no longer present in new_stocks
        stock_data[:] = [stock for stock in stock_data if stock['symbol'] in {s['symbol'] for s in new_stocks}]

        # Add new stocks that are not already in the existing data
        for new_stock in new_stocks:
            if new_stock['symbol'] not in existing_symbols:
                stock_data.append(new_stock)

        print(f"Total stocks currently in stock_data: {len(stock_data)}")
        
        # Get current time in IST using pytz
        ist_timezone = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(ist_timezone)

        # Place orders only at 3:20 PM IST on working days (Monday to Friday)
        if current_time.weekday() < 5 and current_time.hour == 15 and 20 <= current_time.minute <= 29:

            # Place orders for all stocks currently in stock_data
            for stock in stock_data:
                current_price = stock['current_price']
                #print(f"Processing stock: {stock['symbol']} with current price: {current_price}") 
                
                if current_price > 0:  # Ensure price is valid
                    quantity = int(5000 / current_price)  # Calculate quantity as 5000/current_price and round down
                    
                    # Get the correct symbol name before placing the order
                    trading_symbol_name = f"{stock['symbol']}"
                    correct_symbol_name = getSymbolNameFinvasia(api, trading_symbol_name)
                    
                    # Check if an order has already been placed for this symbol using the global ordered_symbols set
                    if correct_symbol_name not in ordered_symbols:
                        print(f"Placing Buy order for {correct_symbol_name}: Quantity={quantity}, Price={current_price}")
                        
                        order_response = placeOrder(api, buy_or_sell='B', tradingsymbol=correct_symbol_name, quantity=quantity)
                        
                        print(f"Order response for {correct_symbol_name}: {order_response}")  # Print each order response
                        
                        # Mark this symbol as ordered
                        ordered_symbols.add(correct_symbol_name)
                    else:
                        print(f"Order already placed for {correct_symbol_name}. Skipping.")
        else:
            print("Not the right time to place orders. Current time:", current_time.strftime("%Y-%m-%d %H:%M:%S"))

    except Exception as e:
        logging.error(f"Error fetching stocks: {e}")

    finally:
        driver.quit()
