import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def get_crypto_price(symbol):
    try:
        coin = symbol.replace("-USD", "").replace("-USDT", "").lower()
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, timeout=10)
        data = r.json()
        if coin in data:
            price = data[coin]["usd"]
            change = data[coin].get("usd_24h_change", 0)
            return price, change
        return None, None
    except Exception as e:
        logger.error(f"Price fetch error: {e}")
        return None, None

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

def get_signal(symbol):
    try:
        ticker = symbol.replace("-USD", "").replace("-USDT", "").upper()
        coin_id = COIN_IDS.get(ticker, ticker.lower())
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
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        change_24h = ((current - prices[-25]) / prices[-25]) * 100 if len(prices) > 25 else 0
        if rsi < 40:
            action = "BUY"
        elif rsi > 60:
            action = "SELL"
        else:
            action = "HOLD"
        entry = round(current, 2)
        target = round(current * 1.05, 2) if action == "BUY" else round(current * 0.95, 2)
        stop_loss = round(current * 0.97, 2) if action == "BUY" else round(current * 1.03, 2)
        return {
            "ticker": ticker,
            "action": action,
            "entry": entry,
            "target": target,
            "stop_loss": stop_loss,
            "rsi": round(rsi, 1),
            "change_24h": round(change_24h, 2)
        }
    except Exception as e:
        logger.error(f"Signal error: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to milli - your personal trading signal bot.\n\n"
        "Get real-time BUY/SELL signals powered by live market data.\n\n"
        "Commands:\n"
        "/signal BTC - Get signal for any crypto\n"
        "/price BTC - Get current price\n"
        "/help - Show all commands"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "milli Help\n\n"
        "/signal BTC - Trading signal with entry, target and stop loss\n"
        "/signal ETH - Works for any major crypto\n"
        "/price SOL - Live price\n"
        "/start - Restart the bot\n\n"
        "Supported: BTC ETH SOL BNB XRP ADA DOGE AVAX LINK"
    )

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = context.args[0].upper() if context.args else "BTC"
    await update.message.reply_text("Fetching signal for " + ticker + "...")
    data = get_signal(ticker)
    if not data:
        await update.message.reply_text("Could not fetch data for " + ticker + ". Try: BTC ETH SOL BNB XRP")
        return
    await update.message.reply_text(
        "Signal: " + data["ticker"] + "\n\n"
        "Action: " + data["action"] + "\n"
        "Entry: $" + str(data["entry"]) + "\n"
        "Target: $" + str(data["target"]) + "\n"
        "Stop Loss: $" + str(data["stop_loss"]) + "\n"
        "RSI: " + str(data["rsi"]) + "\n"
        "24h Change: " + str(data["change_24h"]) + "%"
    )

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = context.args[0].upper() if context.args else "BTC"
    coin_id = COIN_IDS.get(ticker, ticker.lower())
    p, change = get_crypto_price(coin_id)
    if not p:
        await update.message.reply_text("Could not fetch price for " + ticker)
        return
    direction = "+" if change >= 0 else ""
    await update.message.reply_text(
        ticker + " Price\n"
        "$" + str(round(p, 2)) + "\n"
        "24h: " + direction + str(round(change, 2)) + "%"
    )

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("price", price))
    logger.info("Bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()