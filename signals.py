import yfinance as yf


def get_price(ticker: str) -> float | None:
    try:
        t = yf.Ticker(ticker)
        price = t.fast_info.last_price
        if price:
            return float(price)
        hist = t.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None
    except Exception:
        return None


def get_signal(ticker: str) -> dict | None:
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)
        if df is None or df.empty or len(df) < 50:
            return None

        close = df["Close"].squeeze()

        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rsi   = 100 - (100 / (1 + gain / loss))
        current_rsi = float(rsi.iloc[-1])

        ema12        = close.ewm(span=12, adjust=False).mean()
        ema26        = close.ewm(span=26, adjust=False).mean()
        macd_line    = ema12 - ema26
        signal_line  = macd_line.ewm(span=9, adjust=False).mean()
        macd_bullish    = float(macd_line.iloc[-1]) > float(signal_line.iloc[-1])
        macd_crossover  = float(macd_line.iloc[-2]) <= float(signal_line.iloc[-2]) and float(macd_line.iloc[-1]) > float(signal_line.iloc[-1])
        macd_crossunder = float(macd_line.iloc[-2]) >= float(signal_line.iloc[-2]) and float(macd_line.iloc[-1]) < float(signal_line.iloc[-1])

        ema20       = close.ewm(span=20, adjust=False).mean()
        ema50       = close.ewm(span=50, adjust=False).mean()
        ema_uptrend = float(ema20.iloc[-1]) > float(ema50.iloc[-1])

        price   = float(close.iloc[-1])
        bullish = sum([current_rsi < 40, macd_bullish, ema_uptrend])
        bearish = sum([current_rsi > 60, not macd_bullish, not ema_uptrend])

        if current_rsi < 30:
            signal, reason = "BUY",     f"RSI oversold ({current_rsi:.1f})"
        elif current_rsi > 70:
            signal, reason = "SELL",    f"RSI overbought ({current_rsi:.1f})"
        elif macd_crossover and ema_uptrend:
            signal, reason = "BUY",     "MACD bullish crossover + uptrend"
        elif macd_crossunder and not ema_uptrend:
            signal, reason = "SELL",    "MACD bearish crossunder + downtrend"
        elif bullish >= 2:
            signal, reason = "BUY",     f"Bullish momentum ({bullish}/3 indicators)"
        elif bearish >= 2:
            signal, reason = "SELL",    f"Bearish momentum ({bearish}/3 indicators)"
        else:
            signal, reason = "NEUTRAL", "Mixed signals"

        target    = round(price * 1.08, 4) if signal == "BUY"  else round(price * 0.92, 4) if signal == "SELL" else None
        stop_loss = round(price * 0.96, 4) if signal == "BUY"  else round(price * 1.04, 4) if signal == "SELL" else None

        return {
            "signal": signal, "price": price, "target": target, "stop_loss": stop_loss,
            "rsi": current_rsi, "macd_bullish": macd_bullish,
            "macd_crossover": macd_crossover, "macd_crossunder": macd_crossunder,
            "ema_uptrend": ema_uptrend, "reason": reason,
        }
    except Exception as e:
        print(f"Signal error for {ticker}: {e}")
        return None