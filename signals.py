import requests

COIN_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "MATIC": "matic-network",
}

def get_price(ticker):
    try:
        coin_id = COIN_IDS.get(ticker.upper(), ticker.lower())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        r = requests.get(url, timeout=10)
        data = r.json()
        if coin_id in data:
            return data[coin_id]["usd"]
        return None
    except:
        return None

def get_signal(ticker):
    try:
        coin_id = COIN_IDS.get(ticker.upper(), ticker.lower())
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=3&interval=hourly"
        r = requests.get(url, timeout=10)
        data = r.json()
        if "prices" not in data:
            return None
        prices = [p[1] for p in data["prices"]]
        current = prices[-1]
        delta = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in delta]
        losses = [-d if d < 0 else 0 for d in delta]
        avg_gain = sum(gains[-14:]) / 14
        avg_loss = sum(losses[-14:]) / 14
        rsi = 100 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
        if rsi < 40:
            signal = "BUY"
        elif rsi > 60:
            signal = "SELL"
        else:
            signal = "NEUTRAL"
        target = round(current * 1.08, 4) if signal == "BUY" else round(current * 0.92, 4) if signal == "SELL" else None
        stop_loss = round(current * 0.96, 4) if signal == "BUY" else round(current * 1.04, 4) if signal == "SELL" else None
        return {
            "signal": signal,
            "price": round(current, 4),
            "target": target,
            "stop_loss": stop_loss,
            "rsi": round(rsi, 1),
        }
    except Exception as e:
        print(f"Signal error: {e}")
        return None