# trading_utils.py
from NorenRestApiPy.NorenApi import NorenApi

class ShoonyaApiPy(NorenApi):
    def __init__(self):
        NorenApi.__init__(self, host='https://api.shoonya.com/NorenWClientTP/', websocket='wss://api.shoonya.com/NorenWSTP/')

def getPriceBySymbolName(api, tradingSymbolName):
    """Fetch the quote for a given exchange and token."""
    getScriptToken = api.searchscrip(exchange='NSE',searchtext=tradingSymbolName)
    response = api.get_quotes(exchange='NSE', token=getScriptToken['values'][0].get('token'))
    currentPrice = response.get('lp')
    return currentPrice

def place_order(api, buy_or_sell, tradingsymbol, quantity, 
                product_type='C', exchange='NSE', discloseqty=0, 
                price_type='MKT', price=0.0, trigger_price=None, 
                retention='DAY', amo='NO', remarks=None):

    return api.place_order(
        buy_or_sell=buy_or_sell,
        product_type=product_type,
        exchange=exchange,
        tradingsymbol=tradingsymbol,
        quantity=quantity,
        discloseqty=discloseqty,
        price_type=price_type,
        price=price,
        trigger_price=trigger_price,
        retention=retention,
        amo=amo,
        remarks=remarks
    )


