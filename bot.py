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

def get_signal(ticker: str):
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(