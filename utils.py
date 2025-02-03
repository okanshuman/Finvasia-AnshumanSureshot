# utils.py

def round_to_two_decimal(value):
    """Helper function to round a number to two decimal places."""
    return round(value, 2)

def is_valid_symbol(symbol):
    """Check if the symbol is valid (does not contain BEES, ETF, ALPHA, MAFANG, MOREALTY, MOMOMENTUM, or numerics)."""
    return not any(sub in symbol for sub in ["BEES", "ETF", "ALPHA", "MAFANG", "MOREALTY", "MOMOMENTUM", "LIC", "GOLD"]) and not any(
        char.isdigit() for char in symbol)

def clean_symbol(symbol):
    """Remove 'NSE:' prefix from the symbol."""
    return symbol.replace("NSE:", "")

def calculate_percentage_change(cost_price, ltp):
    """Calculate the percentage change based on cost price and last traded price."""
    if cost_price == 0:
        return 0.0  # Avoid division by zero
    return round_to_two_decimal(((ltp - cost_price) / cost_price) * 100)

def ensure_eq_suffix(symbol):
    """
    Ensure the stock symbol ends with '-EQ'. If not, append '-EQ'.
    """
    if not symbol.endswith("-EQ"):
        symbol += "-EQ"
    return symbol