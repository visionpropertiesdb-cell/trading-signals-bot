import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
from signals import get_price, get_signal
from tracker import log_signal, get_stats, get_history, update_open_trades

load_dotenv()

TOKEN         = os.getenv("TELEGRAM_BOT_TOKEN", "")
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL_MINUTES", "60"))
DATA_FILE     = "data.json"

COIN_IDS = {
    "BTC":  "bitcoin",
    "ETH":  "ethereum",
    "BNB":  "binancecoin",
    "SOL":  "solana",
    "XRP":  "ripple",
    "ADA":  "cardano",
    "DOGE": "dogecoin",
}

DEFAULT_TICKERS = list(COIN_IDS.keys())

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

all_users:     set[int]            = set()
subscriptions: dict[int, set[str]] = {}


def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({"users": list(all_users), "subscriptions": {str(k): sorted(v) for k, v in subscriptions.items()}}, f)


def load_data():
    global all_users, subscriptions
    try:
        data          = json.load(open(DATA_FILE))
        all_users     = set(data.get("users", []))
        subscriptions = {int(k): set(v) for k, v in data.get("subscriptions", {}).items()}
    except FileNotFoundError:
        all_users, subscriptions = set(), {}


def format_signal(symbol: str, sig: dict) -> str:
    lines = [
        f"Symbol: {symbol}",
        f"Action: {sig['signal']}",
        f"Entry: ${sig['price']:,.4f}",
    ]
    if sig.get("target") is not None:
        lines.append(f"Target: ${sig['target']:,.4f}")
    if sig.get("stop_loss") is not None:
        lines.append(f"Stop Loss: ${sig['stop_loss']:,.4f}")
    return "\n".join(lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    all_users.add(chat_id)
    save_data()
    await update.message.reply_text(
        "Welcome to milli Signals 📊\n\n"
        "We call BUY/SELL signals on crypto before they move.\n\n"
        "📈 This month: building track record\n"
        "💰 Recent signals: /history to see results\n\n"
        "Commands:\n"
        "/price ETH - Live price\n"
        "/signal BTC - Get signal\n"
        "/scan - Scan all tickers\n"
        "/watchlist - Your tickers\n"
        "/history - Signal track record\n"
        "/stats - Win rate and performance\n\n"
        "🔓 Free: 3 signals/day\n"
        "💎 Premium ($20/mo): Unlimited + early alerts\n\n"
        "👉 /subscribe to upgrade"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "milli Signals — Commands 📊\n\n"
        "/price ETH - Live price\n"
        "/signal BTC - Get signal\n"
        "/scan - Scan all tickers now\n"
        "/watchlist - Your tickers\n"
        "/history - Last 10 signals\n"
        "/stats - Win rate and performance\n"
        "/subscribe - Upgrade to premium\n\n"
        "🔓 Free: 3 signals/day\n"
        "💎 Premium ($20/mo): Unlimited + early alerts"
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_open_trades()
    stats = get_stats()

    if stats["total"] == 0:
        await update.message.reply_text(
            "📊 No signals logged yet.\n\nUse /signal BTC or /scan to generate signals."
        )
        return

    lines = [
        "📊 milli Signals — Performance\n",
        f"Total Signals: {stats['total']}",
        f"Open:          {stats['open']}",
        f"Closed:        {stats['closed']}",
        f"✅ Wins:       {stats['wins']}",
        f"❌ Losses:     {stats['losses']}",
        f"Win Rate:      {stats['win_rate']}%",
    ]
    if stats["avg_win"]:
        lines.append(f"Avg Win:       +{stats['avg_win']}%")
    if stats["avg_loss"]:
        lines.append(f"Avg Loss:      {stats['avg_loss']}%")

    await update.message.reply_text("\n".join(lines))


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_open_trades()
    history = get_history(limit=10)

    if not history:
        await update.message.reply_text(
            "📋 No signals logged yet.\n\nUse /signal BTC or /scan to generate signals."
        )
        return

    lines = ["📋 milli Signals — Last 10 Trades\n"]
    for t in reversed(history):
        status = t["result"] if t["status"] == "CLOSED" else "OPEN"
        pnl    = f" ({t['pnl_pct']:+.1f}%)" if t["pnl_pct"] is not None else ""
        lines.append(f"{t['ticker']} {t['action']} @ ${t['entry']:,.4f} — {status}{pnl}")

    await update.message.reply_text("\n".join(lines))


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 milli Signals Premium\n\n"
        "$20/mo — Unlimited signals + early alerts\n\n"
        "DM @millibot to upgrade."
    )


async def cmd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /price <symbol>  e.g. /price ETH")
        return
    symbol = context.args[0].upper()
    price  = get_price(symbol)
    if price is None:
        await update.message.reply_text(f"Could not fetch price for {symbol}.")
        return
    await update.message.reply_text(f"{symbol}: ${price:,.4f}")


async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /signal <symbol>  e.g. /signal ETH")
        return
    symbol = context.args[0].upper()
    await update.message.reply_text(f"Analyzing {symbol}...")
    sig = get_signal(symbol)
    if sig is None:
        await update.message.reply_text(f"Could not fetch data for {symbol}.")
        return
    if sig["signal"] != "NEUTRAL":
        log_signal(symbol, sig["signal"], sig["price"], sig["target"], sig["stop_loss"])
    await update.message.reply_text(format_signal(symbol, sig))


async def cmd_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    tickers = subscriptions.get(chat_id, set())
    if not tickers:
        await update.message.reply_text("No custom tickers yet.")
        return
    await update.message.reply_text("Your watchlist:\n" + "\n".join(f"- {t}" for t in sorted(tickers)))


async def run_scan(app: Application) -> int:
    sent = 0
    for symbol in DEFAULT_TICKERS:
        sig = get_signal(symbol)
        if sig is None or sig["signal"] == "NEUTRAL":
            continue
        log_signal(symbol, sig["signal"], sig["price"], sig["target"], sig["stop_loss"])
        msg = format_signal(symbol, sig)
        for chat_id in list(all_users):
            try:
                await app.bot.send_message(chat_id=chat_id, text=msg)
                sent += 1
            except Exception as e:
                logger.warning(f"Could not reach {chat_id}: {e}")
    return sent


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Scanning {len(DEFAULT_TICKERS)} tickers...")
    count = await run_scan(context.application)
    await update.message.reply_text(
        f"Done. {count} signal(s) sent." if count else "Done. No actionable signals right now."
    )


async def scan_job(context: ContextTypes.DEFAULT_TYPE):
    if not all_users:
        return
    logger.info("Running scheduled scan...")
    count = await run_scan(context.application)
    logger.info(f"Scan complete. {count} signal(s) sent.")


async def update_trades_job(context: ContextTypes.DEFAULT_TYPE):
    update_open_trades()
    logger.info("Open trades updated.")


def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")
    load_data()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("price",     cmd_price))
    app.add_handler(CommandHandler("signal",    cmd_signal))
    app.add_handler(CommandHandler("scan",      cmd_scan))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("watchlist", cmd_watchlist))
    app.add_handler(CommandHandler("stats",     stats_command))
    app.add_handler(CommandHandler("history",   history_command))
    app.job_queue.run_repeating(scan_job,          interval=SCAN_INTERVAL * 60, first=60)
    app.job_queue.run_repeating(update_trades_job, interval=300,               first=60)
    logger.info(f"Bot started. Scanning {len(DEFAULT_TICKERS)} tickers every {SCAN_INTERVAL} min.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()