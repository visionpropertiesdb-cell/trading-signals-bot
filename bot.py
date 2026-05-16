import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to the Trading Signals Bot!\n\n"
        "Available commands:\n"
        "/start - Show this message\n"
        "/signal - Get the latest trading signal\n"
        "/help - Show help"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Trading Signals Bot Help\n\n"
        "/signal - Fetch the latest trading signal\n"
        "/start - Restart the bot"
    )


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Placeholder — replace with real signal logic
    await update.message.reply_text(
        "📊 Latest Signal\n\n"
        "Symbol: BTC/USDT\n"
        "Action: BUY\n"
        "Entry: $65,000\n"
        "Target: $70,000\n"
        "Stop Loss: $62,000\n\n"
        "(Demo signal — integrate your data source to get real signals)"
    )


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("signal", signal))

    logger.info("Bot started — polling for updates")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
