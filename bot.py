import os
import logging
import yfinance as yf
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def get_signal(ticker):
    try:
        data = yf.download(ticker, period="5d", interval="1h", progress=False)
        if data.empty:
            return None
        close = data["Close"].dropna()
        current_price = float(close.iloc[-1])
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = float((ema12 - ema26).iloc[-1])
        action = "BUY" if rsi < 45 and macd > 0 else "SELL" if rsi > 55 and macd < 0 else "HOLD"
        entry = round(current_price, 2)
        target = round(current_price * 1.05, 2) if action == "BUY" else round(current_price * 0.95, 2)
        stop_loss = round(current_price * 0.97, 2) if action == "BUY" else round(current_price * 1.03, 2)
        return {"ticker": ticker.upper(), "action": action, "entry": entry, "target": target, "stop_loss": stop_loss, "rsi": round(rsi, 1)}
    except Exception as e:
        logger.error(f"Error fetching signal: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to milli - your personal trading signal bot.\n\n"
        "Get real-time BUY/SELL signals powered by live market data.\n\n"
        "Commands:\n"
        "/signal BTC-USD - Get signal for any ticker\n"
        "/price BTC-USD - Get current price\n"
        "/help - Show all commands"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "milli Help\n\n"
        "/signal BTC-USD - Trading signal with entry, target and stop loss\n"
        "/signal AAPL - Works for stocks too\n"
        "/price BTC-USD - Live price for any ticker\n"
        "/start - Restart the bot\n\n"
        "Signals are based on RSI and MACD analysis."
    )

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = context.args[0].upper() if context.args else "BTC-USD"
    await update.message.reply_text("Fetching signal for " + ticker + "...")
    data = get_signal(ticker)
    if not data:
        await update.message.reply_text("Could not fetch data for " + ticker + ". Check the ticker and try again.")
        return
    emoji = "BUY" if data["action"] == "BUY" else "SELL" if data["action"] == "SELL" else "HOLD"
    await update.message.reply_text(
        "Signal: " + data["ticker"] + "\n\n"
        "Action: " + emoji + "\n"
        "Entry: $" + str(data["entry"]) + "\n"
        "Target: $" + str(data["target"]) + "\n"
        "Stop Loss: $" + str(data["stop_loss"]) + "\n"
        "RSI: " + str(data["rsi"])
    )

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = context.args[0].upper() if context.args else "BTC-USD"
    try:
        data = yf.download(ticker, period="1d", interval="1m", progress=False)
        current = float(data["Close"].dropna().iloc[-1])
        await update.message.reply_text(ticker + " - $" + str(round(current, 2)))
    except Exception:
        await update.message.reply_text("Could not fetch price for " + ticker)

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