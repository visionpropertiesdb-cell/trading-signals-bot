import json
import os
from datetime import datetime
import requests

TRADES_FILE = "trades.json"

def load_trades():
    if not os.path.exists(TRADES_FILE):
        return []
    with open(TRADES_FILE, "r") as f:
        return json.load(f)

def save_trades(trades):
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=2)

def log_signal(ticker, action, entry, target, stop_loss):
    trades = load_trades()
    trade = {
        "id": len(trades) + 1,
        "ticker": ticker,
        "action": action,
        "entry": entry,
        "target": target,
        "stop_loss": stop_loss,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "OPEN",
        "close_price": None,
        "result": None,
        "pnl_pct": None
    }
    trades.append(trade)
    save_trades(trades)
    return trade

COIN_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "MATIC": "matic-network",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
}

def get_current_price(ticker):
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

def update_open_trades():
    trades = load_trades()
    updated = False
    for trade in trades:
        if trade["status"] != "OPEN":
            continue
        current = get_current_price(trade["ticker"])
        if not current:
            continue
        action = trade["action"]
        target = trade["target"]
        stop_loss = trade["stop_loss"]
        entry = trade["entry"]
        if action == "BUY":
            if current >= target:
                trade["status"] = "CLOSED"
                trade["result"] = "WIN"
                trade["close_price"] = current
                trade["pnl_pct"] = round(((current - entry) / entry) * 100, 2)
                updated = True
            elif current <= stop_loss:
                trade["status"] = "CLOSED"
                trade["result"] = "LOSS"
                trade["close_price"] = current
                trade["pnl_pct"] = round(((current - entry) / entry) * 100, 2)
                updated = True
        elif action == "SELL":
            if current <= target:
                trade["status"] = "CLOSED"
                trade["result"] = "WIN"
                trade["close_price"] = current
                trade["pnl_pct"] = round(((entry - current) / entry) * 100, 2)
                updated = True
            elif current >= stop_loss:
                trade["status"] = "CLOSED"
                trade["result"] = "LOSS"
                trade["close_price"] = current
                trade["pnl_pct"] = round(((entry - current) / entry) * 100, 2)
                updated = True
    if updated:
        save_trades(trades)
    return trades

def get_stats():
    trades = load_trades()
    closed = [t for t in trades if t["status"] == "CLOSED"]
    open_trades = [t for t in trades if t["status"] == "OPEN"]
    wins = [t for t in closed if t["result"] == "WIN"]
    losses = [t for t in closed if t["result"] == "LOSS"]
    win_rate = round((len(wins) / len(closed)) * 100, 1) if closed else 0
    avg_win = round(sum(t["pnl_pct"] for t in wins) / len(wins), 2) if wins else 0
    avg_loss = round(sum(t["pnl_pct"] for t in losses) / len(losses), 2) if losses else 0
    return {
        "total": len(trades),
        "open": len(open_trades),
        "closed": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss
    }

def get_history(limit=10):
    trades = load_trades()
    return trades[-limit:]