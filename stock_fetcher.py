# stock_fetcher.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
from datetime import datetime
from utils import round_to_two_decimal, is_valid_symbol, clean_symbol

def fetch_stocks(stock_data):
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

            logging.info(f"Found {len(rows)} rows of stock data from {url}.")

            for row in rows:
                columns = row.find_elements(By.TAG_NAME, 'td')
                if len(columns) > 5:  # Ensure there are enough columns to avoid index errors
                    stock_name = columns[1].text.strip()
                    stock_symbol = clean_symbol(columns[2].text.strip().replace('$', ''))  
                    current_price = round_to_two_decimal(float(columns[5].text.strip()))  # Fetch current price
                    identified_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Check if the stock is valid and not already in the list
                    if is_valid_symbol(stock_symbol):
                        new_stocks.append({"name": stock_name, 
                                           "symbol": stock_symbol, 
                                           "current_price": current_price, 
                                           "date": identified_date})

        # Update global stock_data with newly fetched stocks
        # Remove stocks that are no longer present in new_stocks
        existing_symbols = {stock['symbol'] for stock in stock_data}
        new_symbols = {stock['symbol'] for stock in new_stocks}

        # Remove stocks that are not in the new data
        stock_data[:] = [stock for stock in stock_data if stock['symbol'] in new_symbols]

        # Add new stocks that are not already in the existing data
        for new_stock in new_stocks:
            if new_stock['symbol'] not in existing_symbols:
                stock_data.append(new_stock)

    except Exception as e:
        logging.error(f"Error fetching stocks: {e}")

    finally:
        driver.quit()
