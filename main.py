import os
import requests
import pandas as pd
import numpy as np
import feedparser
import json
import time
import pyotp
from groq import Groq
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
CHAT_ID = os.environ["CHAT_ID"]
ANGEL_API_KEY = os.environ["ANGEL_API_KEY"]
ANGEL_CLIENT_ID = os.environ["ANGEL_CLIENT_ID"]
ANGEL_PASSWORD = os.environ["ANGEL_PASSWORD"]
ANGEL_TOTP = os.environ["ANGEL_TOTP"]

client = Groq(api_key=GROQ_API_KEY)

WATCHLIST = {
    "Nifty 50": "99926000",
    "Sensex": "99919000",
    "Bank Nifty": "99926009",
    "Reliance": "2885",
    "TCS": "11536",
    "HDFC Bank": "1333",
    "ICICI Bank": "4963",
    "SBI": "3045",
    "Axis Bank": "5900",
    "Kotak Bank": "1922",
    "Bajaj Finance": "317",
    "Infosys": "1594",
    "HCL Tech": "7229",
    "Wipro": "3787",
    "TechMahindra": "13538",
    "Tata Steel": "3499",
    "JSW Steel": "11723",
    "Hindalco": "1363",
    "Coal India": "20374",
    "NMDC": "15332",
    "ONGC": "2475",
    "BPCL": "526",
    "IOC": "1624",
    "GAIL": "910",
    "IGL": "11262",
    "Maruti": "10999",
    "Tata Motors": "3456",
    "Bajaj Auto": "16669",
    "M&M": "2031",
    "Hero MotoCorp": "1348",
    "Sun Pharma": "3351",
    "Dr Reddy": "881",
    "Cipla": "694",
    "Divis Lab": "10243",
    "Hindustan Unilever": "1394",
    "ITC": "1660",
    "Nestle": "17963",
    "Britannia": "547",
    "DLF": "14732",
    "Godrej Properties": "25371",
    "HAL": "541154",
    "BEL": "383",
    "Bharti Airtel": "10604",
    "NTPC": "11630",
    "Power Grid": "14977",
    "UltraTech Cement": "11532",
    "L&T": "11483",
    "Adani Ports": "15083",
    "Titan": "3506",
    "Asian Paints": "236",
    "Bajaj Finserv": "16675",
    "SBI Life": "21808",
    "HDFC Life": "467",
    "Zomato": "5097",
    "IRFC": "543257",
    "RVNL": "542649",
    "IRCTC": "542769",
    "Dixon Tech": "5321",
    "IndiGo": "11195",
    "Tata Power": "3426",
    "Polycab": "542652",
    "Havells": "11974"
}

GLOBAL_MARKETS = {
    "Dow Jones": "^DJI",
    "Nasdaq": "^IXIC",
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "Gift Nifty": "NQ=F"
}

SECTOR_NEWS_MAP = {
    "rbi": "Banks,NBFCs",
    "repo rate": "Banks,Realty",
    "crude": "Aviation,Oil,Paints",
    "dollar": "IT,Pharma",
    "rupee": "IT,Pharma,Imports",
    "inflation": "FMCG,Banks",
    "monsoon": "FMCG,Agro,Sugar",
    "defence": "HAL,BEL",
    "pli": "Electronics,Auto",
    "fed": "IT,Metals",
    "budget": "Infra,Railways",
    "ukraine": "Metals,Oil",
    "middle east": "Oil,Aviation",
    "interest rate": "Banks,Realty",
    "gdp": "Overall Economy"
}

# ============ ANGEL ONE LOGIN ============
angel_token = None
angel_refresh = None

def angel_login():
    global angel_token, angel_refresh
    try:
        totp = pyotp.TOTP(ANGEL_TOTP).now()
        url = "https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByPassword"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00",
            "X-PrivateKey": ANGEL_API_KEY
        }
        payload = {
            "clientcode": ANGEL_CLIENT_ID,
            "password": ANGEL_PASSWORD,
            "totp": totp
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if data.get("status"):
            angel_token = data["data"]["jwtToken"]
            angel_refresh = data["data"]["refreshToken"]
            return True
        return False
    except Exception as e:
        print(f"Login error: {e}")
        return False

def get_angel_headers():
    return {
        "Authorization": f"Bearer {angel_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00",
        "X-PrivateKey": ANGEL_API_KEY
    }

# ============ GET LIVE PRICE ============
def get_live_price(symbol_token):
    try:
        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote/"
        payload = {
            "mode": "FULL",
            "exchangeTokens": {
                "NSE": [symbol_token]
            }
        }
        resp = requests.post(url, json=payload, headers=get_angel_headers(), timeout=10)
        data = resp.json()
        if data.get("status") and data.get("data"):
            quote = data["data"]["fetched"][0]
            return {
                "ltp": quote.get("ltp", 0),
                "open": quote.get("open", 0),
                "high": quote.get("high", 0),
                "low": quote.get("low", 0),
                "close": quote.get("close", 0),
                "volume": quote.get("tradeVolume", 0),
                "change": quote.get("percentChange", 0)
            }
    except Exception as e:
        print(f"Price error {symbol_token}: {e}")
    return None

# ============ GET HISTORICAL DATA ============
def get_historical(symbol_token, days=90):
    try:
        end = datetime.now()
        start = end - timedelta(days=days)
        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/historical/v1/getCandleData"
        payload = {
            "exchange": "NSE",
            "symboltoken": symbol_token,
            "interval": "ONE_DAY",
            "fromdate": start.strftime("%Y-%m-%d %H:%M"),
            "todate": end.strftime("%Y-%m-%d %H:%M")
        }
        resp = requests.post(url, json=payload, headers=get_angel_headers(), timeout=10)
        data = resp.json()
        if data.get("status") and data.get("data"):
            candles = data["data"]
            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
            df = df.astype({"Open": float, "High": float, "Low": float, "Close": float, "Volume": float})
            return df
    except Exception as e:
        print(f"Historical error {symbol_token}: {e}")
    return pd.DataFrame()

# ============ GLOBAL MARKETS ============
def get_global_markets():
    data = {}
    import yfinance as yf
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

# ============ MACRO DATA ============
def get_macro_data():
    import yfinance as yf
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

# ============ TECHNICAL INDICATORS ============
def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def detect_candle(df):
    try:
        o = float(df["Open"].iloc[-1])
        h = float(df["High"].iloc[-1])
        l = float(df["Low"].iloc[-1])
        c = float(df["Close"].iloc[-1])
        prev_o = float(df["Open"].iloc[-2])
        prev_c = float(df["Close"].iloc[-2])
        body = abs(c - o)
        upper = h - max(o, c)
        lower = min(o, c) - l
        total = h - l
        if total == 0:
            return "No Pattern"
        if body <= total * 0.1:
            return "Doji"
        if lower >= body * 2 and upper <= body * 0.5 and c > o:
            return "Hammer (Bullish)"
        if upper >= body * 2 and lower <= body * 0.5 and c < o:
            return "Shooting Star (Bearish)"
        if c > o and prev_c < prev_o and c > prev_o and o < prev_c:
            return "Bullish Engulfing"
        if c < o and prev_c > prev_o and c < prev_o and o > prev_c:
            return "Bearish Engulfing"
        if c > o and body >= total * 0.7:
            return "Strong Bullish"
        if c < o and body >= total * 0.7:
            return "Strong Bearish"
        return "Normal Candle"
    except:
        return "N/A"

def get_sr(df, price):
    try:
        highs = df["High"].tail(20).values
        lows = df["Low"].tail(20).values
        r_levels = sorted([h for h in highs if h > price])[:2]
        s_levels = sorted([l for l in lows if l < price], reverse=True)[:2]
        return {
            "s1": round(s_levels[0], 2) if s_levels else "N/A",
            "s2": round(s_levels[1], 2) if len(s_levels) > 1 else "N/A",
            "r1": round(r_levels[0], 2) if r_levels else "N/A",
            "r2": round(r_levels[1], 2) if len(r_levels) > 1 else "N/A"
        }
    except:
        return {"s1": "N/A", "s2": "N/A", "r1": "N/A", "r2": "N/A"}

def check_52w(df, price):
    try:
        h52 = round(float(df["High"].max()), 2)
        l52 = round(float(df["Low"].min()), 2)
        if price >= h52 * 0.98:
            return f"Near 52W High ({h52}) BREAKOUT!"
        elif price <= l52 * 1.02:
            return f"Near 52W Low ({l52}) SUPPORT!"
        return f"52W H:{h52} L:{l52}"
    except:
        return "N/A"

def check_circuit(price, prev):
    try:
        chg = ((price - prev) / prev) * 100
        if chg >= 20:
            return "UPPER CIRCUIT!"
        elif chg >= 10:
            return "Near Upper Circuit"
        elif chg <= -20:
            return "LOWER CIRCUIT!"
        elif chg <= -10:
            return "Near Lower Circuit"
        return None
    except:
        return None

# ============ SIGNAL ENGINE ============
def get_signal(token, name):
    try:
        # Get live price
        live = get_live_price(token)
        if not live:
            return None

        price = round(float(live["ltp"]), 2)
        prev = round(float(live["close"]), 2)
        change = round(float(live["change"]), 2)

        if price == 0:
            return None

        # Get historical data
        df = get_historical(token)
        if df.empty or len(df) < 20:
            return None

        close = df["Close"]

        # RSI
        rsi_s = calculate_rsi(close)
        rsi = round(float(rsi_s.iloc[-1]), 1)

        # SMA
        sma20 = round(float(close.rolling(20).mean().iloc[-1]), 2)
        sma50 = round(float(close.rolling(50).mean().iloc[-1]), 2) if len(close) >= 50 else sma20

        # Bollinger Bands
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = round(float((bb_mid + 2 * bb_std).iloc[-1]), 2)
        bb_lower = round(float((bb_mid - 2 * bb_std).iloc[-1]), 2)

        # Volume
        vol = int(live["volume"])
        avg_vol = int(df["Volume"].tail(20).mean())
        vol_sig = "High Vol" if vol > avg_vol * 1.5 else "Normal Vol"

        week_high = round(float(df["High"].tail(5).max()), 2)
        week_low = round(float(df["Low"].tail(5).min()), 2)

        candle = detect_candle(df)
        sr = get_sr(df, price)
        w52 = check_52w(df, price)
        circuit = check_circuit(price, prev)

        # Signal Logic
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
            t1 = round(price * 1.02, 2)
            t2 = round(price * 1.04, 2)
            t3 = round(price * 1.06, 2)
            sl = round(price * 0.97, 2)
        elif signal == "SELL":
            entry_low = round(price * 0.995, 2)
            entry_high = round(price * 1.005, 2)
            t1 = round(price * 0.98, 2)
            t2 = round(price * 0.96, 2)
            t3 = round(price * 0.94, 2)
            sl = round(price * 1.03, 2)
        else:
            entry_low = entry_high = t1 = t2 = t3 = sl = price

        risk = abs(price - sl)
        rr1 = round(abs(t1 - price) / risk, 1) if risk > 0 else 0
        rr2 = round(abs(t2 - price) / risk, 1) if risk > 0 else 0
        trend = "Bullish" if sma20 > sma50 else "Bearish"
        rsi_zone = "Oversold" if rsi < 40 else "Overbought" if rsi > 65 else "Neutral"

        return {
            "name": name,
            "price": price,
            "change": change,
            "signal": signal,
            "confidence": confidence,
            "reason": reason,
            "entry_low": entry_low,
            "entry_high": entry_high,
            "t1": t1, "t2": t2, "t3": t3,
            "sl": sl,
            "rr1": rr1, "rr2": rr2,
            "rsi": rsi,
            "rsi_zone": rsi_zone,
            "trend": trend,
            "sma20": sma20,
            "sma50": sma50,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "week_high": week_high,
            "week_low": week_low,
            "vol_sig": vol_sig,
            "candle": candle,
            "s1": sr["s1"], "s2": sr["s2"],
            "r1": sr["r1"], "r2": sr["r2"],
            "w52": w52,
            "circuit": circuit
        }
    except Exception as e:
        print(f"Signal error {name}: {e}")
        return None

# ============ AI ============
def get_ai_oneliner(name, signal, rsi, trend):
    try:
        prompt = f"Stock: {name}, Signal: {signal}, RSI: {rsi}, Trend: {trend}. Ek line plain Hindi mein (max 10 words) kyun {signal} hai. Koi star mat lagao."
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=40
        )
        return resp.choices[0].message.content.strip()
    except:
        return ""

def get_ai_analysis(macro, global_mkts, news, buy_count, sell_count):
    try:
        prompt = f"""
Tu expert Indian stock market analyst hai.
Crude: {macro.get('crude')} | USD/INR: {macro.get('dollar')}
VIX: {macro.get('vix')} | Gold: {macro.get('gold')}
Dow: {global_mkts.get('Dow Jones')} | Gift Nifty: {global_mkts.get('Gift Nifty')}
NEWS: {news[:2]}
BUY signals: {buy_count} | SELL signals: {sell_count}

Plain Hindi mein sirf 3 lines do.
Koi star ya asterisk bilkul mat lagao.
Seedha likho:
"""
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return resp.choices[0].message.content.strip()
    except:
        return "AI analysis unavailable"

# ============ TELEGRAM ============
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    })

# ============ MAIN ============
def main():
    print("Logging into Angel One...")
    if not angel_login():
        send_telegram("Angel One login failed! Check credentials.")
        return
    print("Login successful!")

    macro = get_macro_data()
    global_mkts = get_global_markets()
    news = get_news()
    sector_impact = get_sector_impact(news)
    fii_dii = get_fii_dii()

    hour = (datetime.utcnow().hour + 5) % 24
    if hour < 12:
        session = "MORNING"
        session_hi = "Subah 9:15 AM"
    elif hour < 15:
        session = "MIDDAY"
        session_hi = "Dopahar 12 PM"
    else:
        session = "CLOSING"
        session_hi = "Shaam 3:30 PM"

    report = f"<b>DalalStreet {session} REPORT</b>\n"
    report += f"<b>{session_hi}</b>\n"
    report += "================================\n\n"

    report += "<b>GLOBAL MARKETS</b>\n"
    for name, val in global_mkts.items():
        report += f"{name}: {val}\n"

    report += "\n<b>MACRO DATA</b>\n"
    report += f"Crude: ${macro.get('crude')} | Gold: ${macro.get('gold')}\n"
    report += f"USD/INR: {macro.get('dollar')} | VIX: {macro.get('vix')}\n"
    report += f"Silver: ${macro.get('silver')} | US10Y: {macro.get('us10y')}%\n"

    report += f"\n<b>FII/DII</b>\n{fii_dii}\n"

    report += "\n<b>NEWS IMPACT</b>\n"
    for s in sector_impact:
        report += f"- {s}\n"

    report += "\n<b>TOP NEWS</b>\n"
    for n in news[:3]:
        report += f"- {n[:80]}\n"

    buy_signals = []
    sell_signals = []
    circuit_alerts = []
    breakout_alerts = []

    print("Fetching signals...")
    for name, token in WATCHLIST.items():
        data = get_signal(token, name)
        if not data:
            continue
        if data["circuit"]:
            circuit_alerts.append(f"{name}: {data['circuit']}")
        if data["w52"] and ("BREAKOUT" in data["w52"] or "SUPPORT" in data["w52"]):
            breakout_alerts.append(f"{name}: {data['w52']}")
        if data["signal"] == "BUY":
            buy_signals.append(data)
        elif data["signal"] == "SELL":
            sell_signals.append(data)
        time.sleep(0.3)

    buy_signals.sort(key=lambda x: x["confidence"], reverse=True)
    sell_signals.sort(key=lambda x: x["confidence"], reverse=True)

    if circuit_alerts:
        report += "\n<b>CIRCUIT ALERTS</b>\n"
        for a in circuit_alerts:
            report += f"- {a}\n"

    if breakout_alerts:
        report += "\n<b>52W BREAKOUT</b>\n"
        for a in breakout_alerts[:3]:
            report += f"- {a}\n"

    report += f"\n<b>SIGNALS — BUY:{len(buy_signals)} | SELL:{len(sell_signals)}</b>\n"
    report += "================================\n"

    for data in buy_signals[:4]:
        ai = get_ai_oneliner(data["name"], "BUY", data["rsi"], data["trend"])
        report += f"\n<b>BUY - {data['name']}</b>\n"
        report += f"Price: {data['price']} ({data['change']:+.2f}%)\n"
        report += f"Entry: {data['entry_low']} - {data['entry_high']}\n"
        report += f"T1: {data['t1']} (R:R 1:{data['rr1']}) | T2: {data['t2']} (R:R 1:{data['rr2']})\n"
        report += f"T3: {data['t3']} | SL: {data['sl']}\n"
        report += f"Support: {data['s1']} / {data['s2']}\n"
        report += f"Resist: {data['r1']} / {data['r2']}\n"
        report += f"BB: {data['bb_lower']} - {data['bb_upper']}\n"
        report += f"RSI: {data['rsi']} ({data['rsi_zone']}) | Trend: {data['trend']}\n"
        report += f"SMA20: {data['sma20']} | SMA50: {data['sma50']}\n"
        report += f"Candle: {data['candle']} | Vol: {data['vol_sig']}\n"
        report += f"{data['w52']}\n"
        report += f"Confidence: {data['confidence']}/10\n"
        if ai:
            report += f"AI: {ai}\n"
        report += "- - - - - - - - -\n"

    for data in sell_signals[:2]:
        ai = get_ai_oneliner(data["name"], "SELL", data["rsi"], data["trend"])
        report += f"\n<b>SELL - {data['name']}</b>\n"
        report += f"Price: {data['price']} ({data['change']:+.2f}%)\n"
        report += f"Entry: {data['entry_low']} - {data['entry_high']}\n"
        report += f"T1: {data['t1']} (R:R 1:{data['rr1']}) | T2: {data['t2']} (R:R 1:{data['rr2']})\n"
        report += f"T3: {data['t3']} | SL: {data['sl']}\n"
        report += f"Support: {data['s1']} / {data['s2']}\n"
        report += f"Resist: {data['r1']} / {data['r2']}\n"
        report += f"BB: {data['bb_lower']} - {data['bb_upper']}\n"
        report += f"RSI: {data['rsi']} ({data['rsi_zone']}) | Trend: {data['trend']}\n"
        report += f"SMA20: {data['sma20']} | SMA50: {data['sma50']}\n"
        report += f"Candle: {data['candle']} | Vol: {data['vol_sig']}\n"
        report += f"{data['w52']}\n"
        report += f"Confidence: {data['confidence']}/10\n"
        if ai:
            report += f"AI: {ai}\n"
        report += "- - - - - - - - -\n"

    if len(report) > 3800:
        cut = report[:3700]
        last_nl = cut.rfind('\n')
        report = report[:last_nl] if last_nl > 3000 else cut

    send_telegram(report)

    # AI analysis alag message
    ai_text = get_ai_analysis(macro, global_mkts, news, len(buy_signals), len(sell_signals))
    ai_msg = "<b>AI ANALYSIS</b>\n" + ai_text + "\n\n<i>DYOR. Not financial advice.</i>"
    send_telegram(ai_msg)

    print("Done!")

if __name__ == "__main__":
    main()
