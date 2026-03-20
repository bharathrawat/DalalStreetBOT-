import os
import requests
import yfinance as yf
import pandas as pd
import feedparser
import json
import numpy as np
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from groq import Groq
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
CHAT_ID = os.environ["CHAT_ID"]

client = Groq(api_key=GROQ_API_KEY)

WATCHLIST = {
    # === INDICES ===
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "Bank Nifty": "^NSEBANK",
    # === BANKING ===
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "SBI": "SBIN.NS",
    "Axis Bank": "AXISBANK.NS",
    "Kotak Bank": "KOTAKBANK.NS",
    # === FINANCIAL ===
    "Bajaj Finance": "BAJFINANCE.NS",
    "Angel One": "ANGELONE.NS",
    "LIC": "LICI.NS",
    "HDFC Life": "HDFCLIFE.NS",
    "SBI Life": "SBILIFE.NS",
    # === IT ===
    "TCS": "TCS.NS",
    "Infosys": "INFY.NS",
    "HCL Tech": "HCLTECH.NS",
    "Dixon Tech": "DIXON.NS",
    # === METALS ===
    "Tata Steel": "TATASTEEL.NS",
    "JSW Steel": "JSWSTEEL.NS",
    "Hindalco": "HINDALCO.NS",
    "Coal India": "COALINDIA.NS",
    "NMDC": "NMDC.NS",
    "MIDHANI": "MIDHANI.NS",
    # === OIL & GAS ===
    "Reliance": "RELIANCE.NS",
    "ONGC": "ONGC.NS",
    "BPCL": "BPCL.NS",
    "IGL": "IGL.NS",
    "GAIL": "GAIL.NS",
    # === AGRO ===
    "Adani Wilmar": "AWL.NS",
    "Coromandel": "COROMANDEL.NS",
    "UPL": "UPL.NS",
    "Balrampur Chini": "BALRAMCHIN.NS",
    # === AUTO ===
    "Maruti": "MARUTI.NS",
    "Tata Motors": "TATAMOTORS.NS",
    "Bajaj Auto": "BAJAJ-AUTO.NS",
    "Bharat Forge": "BHARATFORG.NS",
    "Apollo Tyres": "APOLLOTYRE.NS",
    # === PHARMA ===
    "Sun Pharma": "SUNPHARMA.NS",
    "Dr Reddy": "DRREDDY.NS",
    "Cipla": "CIPLA.NS",
    # === FMCG ===
    "Hindustan Unilever": "HINDUNILVR.NS",
    "ITC": "ITC.NS",
    "Nestle": "NESTLEIND.NS",
    # === CEMENT & INFRA ===
    "UltraTech Cement": "ULTRACEMCO.NS",
    "L&T": "LT.NS",
    "DLF": "DLF.NS",
    # === POWER & CAPITAL GOODS ===
    "NTPC": "NTPC.NS",
    "Power Grid": "POWERGRID.NS",
    "Havells": "HAVELLS.NS",
    "Polycab": "POLYCAB.NS",
    # === DEFENCE ===
    "HAL": "HAL.NS",
    "BEL": "BEL.NS",
    "Mazagon Dock": "MAZDOCK.NS",
    # === TRANSPORT ===
    "IndiGo": "INDIGO.NS",
    "SCI": "SCI.NS",
    "Delhivery": "DELHIVERY.NS",
    # === RAILWAYS ===
    "IRFC": "IRFC.NS",
    "RVNL": "RVNL.NS",
    "IRCTC": "IRCTC.NS",
    # === TELECOM ===
    "Bharti Airtel": "BHARTIARTL.NS",
    "Indus Towers": "INDUSTOWER.NS",
    # === CONSUMER ===
    "Titan": "TITAN.NS",
    "DMart": "DMART.NS",
    "Voltas": "VOLTAS.NS",
    # === MEDIA & E-COMM ===
    "Zomato": "ZOMATO.NS",
    "Sun TV": "SUNTV.NS",
    "PVR Inox": "PVRINOX.NS",
    # === CHEMICALS ===
    "Pidilite": "PIDILITIND.NS",
    "Asian Paints": "ASIANPAINT.NS",
    "SRF": "SRF.NS",
    # === HOTELS & QSR ===
    "IHCL": "INDHOTEL.NS",
    "Jubilant FoodWorks": "JUBLFOOD.NS",
}
GLOBAL_MARKETS = {
    "Dow Jones": "^DJI",
    "Nasdaq": "^IXIC",
    "S&P 500": "^GSPC",
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "Gift Nifty": "NQ=F"
}

SECTOR_NEWS_MAP = {
    "rbi": "Banks,NBFCs",
    "repo rate": "Banks,Realty,NBFCs",
    "crude": "Aviation,Oil,Paints,Petrochemicals",
    "dollar": "IT,Pharma,Exports",
    "rupee": "IT,Pharma,Imports",
    "inflation": "FMCG,Banks,RBI",
    "cpi": "FMCG,Banks",
    "monsoon": "FMCG,Agro,Sugar,Fertilizers",
    "defence": "HAL,BEL,Shipbuilding",
    "pli": "Electronics,Auto,IT Hardware",
    "fed": "IT,Metals,Global",
    "china": "Metals,Electronics,Chemicals",
    "us tariff": "IT,Pharma,Exports",
    "fii": "Overall Market",
    "dii": "Overall Market",
    "budget": "Infra,Railways,Defence,Capital Goods",
    "gst": "FMCG,Auto,Consumer",
    "ukraine": "Metals,Oil,Defence",
    "middle east": "Oil,Aviation,Defence",
    "interest rate": "Banks,Realty,NBFCs",
    "gdp": "Overall Economy",
    "freight": "Shipping,Logistics",
    "pharma": "Pharma,Healthcare",
    "telecom": "Telecom,IT Infrastructure",
    "real estate": "Realty,Cement,Cables",
    "gold": "Jewellery,Safe Haven",
    "sugar": "Sugar,FMCG",
    "semiconductor": "IT Hardware,Electronics"
}

# ============ MACRO DATA ============
def get_macro_data():
    data = {}
    symbols = {
        "crude": "CL=F",
        "dollar": "USDINR=X",
        "vix": "^INDIAVIX",
        "gold": "GC=F",
        "silver": "SI=F",
        "us10y": "^TNX"
    }
    for key, symbol in symbols.items():
        try:
            t = yf.Ticker(symbol)
            data[key] = round(t.fast_info.last_price, 2)
        except:
            data[key] = "N/A"
    return data

# ============ GLOBAL MARKETS ============
def get_global_markets():
    data = {}
    for name, symbol in GLOBAL_MARKETS.items():
        try:
            t = yf.Ticker(symbol)
            price = round(t.fast_info.last_price, 2)
            prev = round(t.fast_info.previous_close, 2)
            change = round(((price - prev) / prev) * 100, 2)
            sign = "+" if change > 0 else ""
            data[name] = f"{price} ({sign}{change}%)"
        except:
            data[name] = "N/A"
    return data

# ============ FII/DII ============
def get_fii_dii():
    try:
        url = "https://www.moneycontrol.com/rss/fiidiiactivity.xml"
        feed = feedparser.parse(url)
        if feed.entries:
            return feed.entries[0].title
        return "FII/DII data unavailable"
    except:
        return "FII/DII data unavailable"

# ============ NEWS ============
def get_news():
    news_list = []
    try:
        url = "https://news.google.com/rss/search?q=india+stock+market+nifty+sensex&hl=en-IN&gl=IN&ceid=IN:en"
        feed = feedparser.parse(url)
        for entry in feed.entries[:8]:
            news_list.append(entry.title)
    except:
        news_list.append("News fetch failed")
    return news_list

def get_sector_impact(news_list):
    impacted = []
    for news in news_list:
        news_lower = news.lower()
        for keyword, sectors in SECTOR_NEWS_MAP.items():
            if keyword in news_lower:
                impact = f"{keyword.upper()} -> {sectors}"
                if impact not in impacted:
                    impacted.append(impact)
    return impacted[:5] if impacted else ["No major sector trigger today"]

# ============ OPTIONS DATA ============
def get_options_data():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com"
        }
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        resp = session.get(url, headers=headers, timeout=5)
        data = resp.json()
        records = data["records"]["data"]
        total_ce_oi = 0
        total_pe_oi = 0
        strike_oi = {}
        for record in records:
            if "CE" in record:
                total_ce_oi += record["CE"].get("openInterest", 0)
            if "PE" in record:
                pe_oi = record["PE"].get("openInterest", 0)
                total_pe_oi += pe_oi
                strike = record["strikePrice"]
                strike_oi[strike] = strike_oi.get(strike, 0) + pe_oi + record.get("CE", {}).get("openInterest", 0)
        pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0
        max_pain = max(strike_oi, key=strike_oi.get) if strike_oi else "N/A"
        pcr_signal = "Bullish" if pcr > 1.2 else "Bearish" if pcr < 0.8 else "Neutral"
        return {"pcr": pcr, "pcr_signal": pcr_signal, "max_pain": max_pain, "total_ce_oi": total_ce_oi, "total_pe_oi": total_pe_oi}
    except:
        return {"pcr": "N/A", "pcr_signal": "N/A", "max_pain": "N/A", "total_ce_oi": "N/A", "total_pe_oi": "N/A"}

# ============ EARNINGS CALENDAR ============
def get_earnings_calendar():
    earnings = []
    important = {"Reliance": "RELIANCE.NS", "TCS": "TCS.NS", "HDFC Bank": "HDFCBANK.NS", "Infosys": "INFY.NS", "SBI": "SBIN.NS"}
    try:
        for name, symbol in important.items():
            t = yf.Ticker(symbol)
            cal = t.calendar
            if cal is not None and not cal.empty:
                if "Earnings Date" in cal.index:
                    earn_date = cal.loc["Earnings Date"].iloc[0]
                    days_left = (earn_date.date() - datetime.now().date()).days
                    if 0 <= days_left <= 7:
                        earnings.append(f"{name}: {earn_date.strftime('%d %b')} ({days_left}d)")
    except:
        pass
    return earnings if earnings else ["No major earnings this week"]

# ============ TECHNICAL INDICATORS ============
def calculate_rsi(data, period=14):
    delta = data["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def detect_candlestick_pattern(df):
    try:
        o = float(df["Open"].iloc[-1])
        h = float(df["High"].iloc[-1])
        l = float(df["Low"].iloc[-1])
        c = float(df["Close"].iloc[-1])
        prev_o = float(df["Open"].iloc[-2])
        prev_c = float(df["Close"].iloc[-2])
        body = abs(c - o)
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        total_range = h - l
        if total_range == 0:
            return "No Pattern"
        if body <= total_range * 0.1:
            return "Doji (Indecision)"
        if lower_wick >= body * 2 and upper_wick <= body * 0.5 and c > o:
            return "Hammer (Bullish)"
        if upper_wick >= body * 2 and lower_wick <= body * 0.5 and c < o:
            return "Shooting Star (Bearish)"
        if c > o and prev_c < prev_o and c > prev_o and o < prev_c:
            return "Bullish Engulfing"
        if c < o and prev_c > prev_o and c < prev_o and o > prev_c:
            return "Bearish Engulfing"
        if c > o and body >= total_range * 0.7:
            return "Strong Bullish Candle"
        if c < o and body >= total_range * 0.7:
            return "Strong Bearish Candle"
        return "Normal Candle"
    except:
        return "N/A"

def get_support_resistance(df):
    try:
        highs = df["High"].tail(20).values
        lows = df["Low"].tail(20).values
        price = float(df["Close"].iloc[-1])
        resistance_levels = sorted([h for h in highs if h > price])[:2]
        support_levels = sorted([l for l in lows if l < price], reverse=True)[:2]
        r1 = round(resistance_levels[0], 2) if len(resistance_levels) > 0 else "N/A"
        r2 = round(resistance_levels[1], 2) if len(resistance_levels) > 1 else "N/A"
        s1 = round(support_levels[0], 2) if len(support_levels) > 0 else "N/A"
        s2 = round(support_levels[1], 2) if len(support_levels) > 1 else "N/A"
        return {"s1": s1, "s2": s2, "r1": r1, "r2": r2}
    except:
        return {"s1": "N/A", "s2": "N/A", "r1": "N/A", "r2": "N/A"}

def check_52week_breakout(df, price):
    try:
        high_52w = round(float(df["High"].tail(252).max()), 2)
        low_52w = round(float(df["Low"].tail(252).min()), 2)
        if price >= high_52w * 0.98:
            return f"Near 52W High ({high_52w}) BREAKOUT!"
        elif price <= low_52w * 1.02:
            return f"Near 52W Low ({low_52w}) SUPPORT!"
        else:
            return f"52W H:{high_52w} L:{low_52w}"
    except:
        return "N/A"

def check_circuit_breaker(price, prev_close):
    try:
        change_pct = ((price - prev_close) / prev_close) * 100
        if change_pct >= 20:
            return "UPPER CIRCUIT (20%+)"
        elif change_pct >= 10:
            return "Near Upper Circuit (10%+)"
        elif change_pct <= -20:
            return "LOWER CIRCUIT (-20%)"
        elif change_pct <= -10:
            return "Near Lower Circuit (-10%)"
        else:
            return None
    except:
        return None

# ============ PAPER TRADE TRACKER ============
def get_paper_trade_summary():
    try:
        gist_token = os.environ.get("GITHUB_TOKEN", "")
        gist_id = os.environ.get("GIST_ID", "")
        if not gist_id:
            return None
        headers = {"Authorization": f"token {gist_token}"}
        resp = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
        gist = resp.json()
        content = gist["files"]["trades.json"]["content"]
        trades = json.loads(content)
        results = []
        win = 0
        loss = 0
        for trade in trades[-10:]:
            symbol = trade.get("symbol")
            entry = trade.get("entry_price")
            signal = trade.get("signal")
            try:
                t = yf.Ticker(symbol)
                current = round(t.fast_info.last_price, 2)
                if signal == "BUY":
                    pnl = round(((current - entry) / entry) * 100, 2)
                else:
                    pnl = round(((entry - current) / entry) * 100, 2)
                status = "WIN" if pnl > 0 else "LOSS"
                if pnl > 0:
                    win += 1
                else:
                    loss += 1
                results.append(f"{trade.get('name')}: {signal} @{entry} -> {current} ({pnl:+.2f}%) {status}")
            except:
                pass
        total = win + loss
        accuracy = round((win / total) * 100, 1) if total > 0 else 0
        return {"results": results, "win": win, "loss": loss, "accuracy": accuracy}
    except:
        return None

# ============ AI ONE-LINER ============
def get_ai_oneliner(name, signal, rsi, trend, reason):
    try:
        prompt = f"Stock: {name}, Signal: {signal}, RSI: {rsi}, Trend: {trend}. Ek line Hindi mein (max 12 words) kyun {signal} hai."
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=40
        )
        return response.choices[0].message.content.strip()
    except:
        return ""

# ============ MAIN SIGNAL ENGINE ============
def get_signal(symbol, name):
    try:
        df = yf.download(symbol, period="3mo", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 20:
            return None

        # Fix yfinance multi-level columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df["Close"].squeeze()
        volume_s = df["Volume"].squeeze()
        high_s = df["High"].squeeze()
        low_s = df["Low"].squeeze()
        open_s = df["Open"].squeeze()

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi = round(float(rsi_series.iloc[-1]), 1)

        # SMA
        sma20 = float(close.rolling(20).mean().iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])

        # Bollinger Bands
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = round(float((bb_mid + 2 * bb_std).iloc[-1]), 2)
        bb_lower = round(float((bb_mid - 2 * bb_std).iloc[-1]), 2)

        price = round(float(close.iloc[-1]), 2)
        prev = round(float(close.iloc[-2]), 2)
        change = round(((price - prev) / prev) * 100, 2)
        volume = int(volume_s.iloc[-1])
        avg_vol = int(volume_s.tail(20).mean())
        vol_signal = "High Vol" if volume > avg_vol * 1.5 else "Normal Vol"
        week_high = round(float(high_s.tail(5).max()), 2)
        week_low = round(float(low_s.tail(5).min()), 2)

        # Build simple df for helper functions
        simple_df = pd.DataFrame({
            "Open": open_s,
            "High": high_s,
            "Low": low_s,
            "Close": close,
            "Volume": volume_s
        })
        candle = detect_candlestick_pattern(simple_df)
        sr = get_support_resistance(simple_df)
        breakout_52w = check_52week_breakout(simple_df, price)
        circuit = check_circuit_breaker(price, prev)

        signal = "HOLD"
        confidence = 5
        reason = ""

        if rsi < 35 and price > sma20:
            signal = "BUY"
            confidence = 9
            reason = "RSI strongly oversold + above SMA20"
        elif rsi < 45 and sma20 > sma50:
            signal = "BUY"
            confidence = 8
            reason = "RSI oversold + bullish trend"
        elif rsi < 50 and sma20 > sma50 and change > 0:
            signal = "BUY"
            confidence = 7
            reason = "RSI low + bullish + price rising"
        elif rsi > 75 and price < sma20:
            signal = "SELL"
            confidence = 9
            reason = "RSI strongly overbought + below SMA20"
        elif rsi > 65 and sma20 < sma50:
            signal = "SELL"
            confidence = 8
            reason = "RSI high + bearish trend"
        elif rsi > 60 and price < sma20 and change < 0:
            signal = "SELL"
            confidence = 7
            reason = "RSI high + below SMA20 + falling"
        else:
            signal = "HOLD"
            confidence = 5
            reason = f"RSI neutral ({rsi})"

        if signal == "BUY":
            entry_low = round(price * 0.995, 2)
            entry_high = round(price * 1.005, 2)
            target1 = round(price * 1.02, 2)
            target2 = round(price * 1.04, 2)
            target3 = round(price * 1.06, 2)
            stoploss = round(price * 0.97, 2)
        elif signal == "SELL":
            entry_low = round(price * 0.995, 2)
            entry_high = round(price * 1.005, 2)
            target1 = round(price * 0.98, 2)
            target2 = round(price * 0.96, 2)
            target3 = round(price * 0.94, 2)
            stoploss = round(price * 1.03, 2)
        else:
            entry_low = entry_high = price
            target1 = target2 = target3 = stoploss = price

        risk = abs(price - stoploss)
        rr1 = round(abs(target1 - price) / risk, 1) if risk > 0 else 0
        rr2 = round(abs(target2 - price) / risk, 1) if risk > 0 else 0
        trend = "Bullish" if sma20 > sma50 else "Bearish"
        rsi_zone = "Oversold" if rsi < 40 else "Overbought" if rsi > 65 else "Neutral"

        return {
            "name": name, "symbol": symbol, "price": price, "prev": prev,
            "change": change, "signal": signal, "confidence": confidence,
            "reason": reason, "entry_low": entry_low, "entry_high": entry_high,
            "target1": target1, "target2": target2, "target3": target3,
            "stoploss": stoploss, "rr1": rr1, "rr2": rr2, "rsi": rsi,
            "rsi_zone": rsi_zone, "trend": trend, "sma20": round(sma20, 2),
            "sma50": round(sma50, 2), "bb_upper": bb_upper, "bb_lower": bb_lower,
            "week_high": week_high, "week_low": week_low, "vol_signal": vol_signal,
            "candle": candle, "support1": sr["s1"], "support2": sr["s2"],
            "resist1": sr["r1"], "resist2": sr["r2"], "breakout_52w": breakout_52w,
            "circuit": circuit
        }
    except:
        return None

# ============ AI ANALYSIS ============
def get_ai_analysis(macro, global_mkts, news, signals_text, buy_count, sell_count, options):
    prompt = f"""
Tu expert Indian stock market analyst hai.
Crude: {macro.get('crude')} | USD/INR: {macro.get('dollar')}
VIX: {macro.get('vix')} | Gold: {macro.get('gold')}
Dow: {global_mkts.get('Dow Jones')} | Gift Nifty: {global_mkts.get('Gift Nifty')}
PCR: {options.get('pcr')} ({options.get('pcr_signal')}) | Max Pain: {options.get('max_pain')}
NEWS: {news[:3]}
BUY: {buy_count} | SELL: {sell_count}
Signals: {signals_text[:200]}

Concise Hindi mein 4 points:
1. Market mood
2. Best opportunity
3. Kya avoid karo
4. Risk warning
"""
    response = client.chat.completions.create(
        model="llama-
