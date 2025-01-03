# app.py
from order_management import *
import credentials as cr

# Initialize API
api = ShoonyaApiPy()
api.login(userid=cr.user, password=cr.pwd, twoFA=cr.factor2, vendor_code=cr.vc, api_secret=cr.app_key, imei=cr.imei)

# Fetch Current Price
#symbolName='Reliance'
#currentPrice = getPriceBySymbolName(api, tradingSymbolName=symbolName)
#print(f"Current Price of {symbolName} : {currentPrice}")

# Place Order
#order_response = place_order(api,buy_or_sell='B',tradingsymbol='RELIANCE-EQ',quantity=100)
#print(order_response)

