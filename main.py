import os, pytz
import requests
import pandas as pd
import numpy as np
import feedparser
import json
import time
import pyotp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
from groq import Groq
from datetime import datetime, timedelta
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
CHAT_ID = os.environ["CHAT_ID"]
ANGEL_API_KEY = os.environ["ANGEL_API_KEY"]
ANGEL_CLIENT_ID = os.environ["ANGEL_CLIENT_ID"]
ANGEL_PASSWORD = os.environ["ANGEL_PASSWORD"]
ANGEL_TOTP = os.environ["ANGEL_TOTP"]
IST = pytz.timezone('Asia/Kolkata')

def is_market_open():
    now = datetime.now(IST)
    # 1. Weekend Check (Sat=5, Sun=6)
    if now.weekday() >= 5:
        return False, "OFF: Aaj Weekend hai, Market band hai."
    
    # 2. Trading Hours (9:00 AM se 3:45 PM)
    market_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_end = now.replace(hour=15, minute=45, second=0, microsecond=0)
    
    if not (market_start <= now <= market_end):
        return False, "OFF: Market hours khatam ho chuke hain."
        
    return True, "ON: Market Active hai!"

client = Groq(api_key=GROQ_API_KEY)

WATCHLIST = {
    # Large Cap
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
    "Tech Mahindra": "13538",
    # Metals
    "Tata Steel": "3499",
    "JSW Steel": "11723",
    "Hindalco": "1363",
    "Coal India": "20374",
    "NMDC": "15332",
    "SAIL": "3147",
    # Energy & Oil
    "ONGC": "2475",
    "BPCL": "526",
    "GAIL": "910",
    "IGL": "11262",
    "Tata Power": "4329",
    "Adani Green": "542798",
    "JSW Energy": "539254",
    # Auto
    "Maruti": "10999",
    "Tata Motors": "3456",
    "Bajaj Auto": "16669",
    "Hero Motocorp": "1348",
    "Eicher Motors": "910",
    "TVS Motor": "532343",
    # Pharma
    "Sun Pharma": "3351",
    "Dr Reddy": "881",
    "Cipla": "694",
    "Aurobindo": "524804",
    "Torrent Pharma": "500420",
    # FMCG & Consumer
    "Hindustan Unilever": "1394",
    "ITC": "1660",
    "Nestle": "17963",
    "Varun Beverages": "540180",
    "Trent": "503657",
    # Infra & Realty
    "DLF": "14732",
    "L&T": "11483",
    "Adani Ports": "15083",
    "UltraTech Cement": "11532",
    # Defence & PSU
    "HAL": "541154",
    "BEL": "383",
    "NTPC": "11630",
    "Power Grid": "14977",
    "HPCL": "1406",
    # Banking
    "PNB": "2730",
    "Bank of Baroda": "1452",
    "Yes Bank": "11915",
    # IT & Electronics
    "Dixon Tech": "5321",
    "Polycab": "542652",
    "Havells": "11974",
    # Others
    "Bharti Airtel": "10604",
    "Titan": "3506",
    "Asian Paints": "236",
    "Zomato": "5097",
    "IRFC": "543257",
    "RVNL": "542649",
    "IRCTC": "542769",
    "IndiGo": "11195",
    "Avenue Supermarts": "543964",
}

GLOBAL_MARKETS = {
    "Dow Jones": "^DJI",
    "Nasdaq": "^IXIC",
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "Gift Nifty": "NQ=F"
}

SECTOR_MAP = {
    "Banking": ["SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak Bank", "PNB", "Bank of Baroda", "Yes Bank", "Bajaj Finance"],
    "IT": ["TCS", "Infosys", "HCL Tech", "Wipro", "Tech Mahindra"],
    "Pharma": ["Sun Pharma", "Dr Reddy", "Cipla", "Aurobindo", "Torrent Pharma"],
    "Auto": ["Maruti", "Tata Motors", "Bajaj Auto", "Hero Motocorp", "Eicher Motors", "TVS Motor"],
    "Energy": ["ONGC", "BPCL", "GAIL", "IGL", "Tata Power", "Adani Green", "NTPC", "Power Grid"],
    "Metals": ["Tata Steel", "JSW Steel", "Hindalco", "Coal India", "NMDC", "SAIL"],
    "FMCG": ["Hindustan Unilever", "ITC", "Nestle", "Varun Beverages"],
    "Infra": ["DLF", "L&T", "Adani Ports", "UltraTech Cement", "RVNL"],
}

SECTOR_NEWS_MAP = {
    "rbi": "Banks,NBFCs",
    "repo rate": "Banks,Realty",
    "crude": "Aviation,Oil,Paints",
    "dollar": "IT,Pharma",
    "inflation": "FMCG,Banks",
    "monsoon": "FMCG,Agro,Sugar",
    "defence": "HAL,BEL",
    "pli": "Electronics,Auto",
    "fed": "IT,Metals",
    "budget": "Infra,Railways",
    "ukraine": "Metals,Oil",
    "middle east": "Oil,Aviation"
}

DISCLAIMER = (
    "\n⚠️ <i>DISCLAIMER: Ye signals technical analysis par based hain "
    "aur sirf educational purpose ke liye hain. Ye SEBI registered "
    "advice nahi hai. Apna risk khud samjho.\n"
    "📌 Do Your Own Research</i>"
)

# ============ ANGEL ONE LOGIN ============
angel_token = None

def angel_login():
    global angel_token
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
            return True
        print(f"Login failed: {data}")
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

# ============ LIVE PRICE ============
def get_live_price(symbol_token):
    try:
        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote/"
        payload = {"mode": "FULL", "exchangeTokens": {"NSE": [symbol_token]}}
        resp = requests.post(url, json=payload, headers=get_angel_headers(), timeout=10)
        data = resp.json()
        if data.get("status") and data.get("data"):
            q = data["data"]["fetched"][0]
            return {
                "ltp": q.get("ltp", 0),
                "open": q.get("open", 0),
                "high": q.get("high", 0),
                "low": q.get("low", 0),
                "close": q.get("close", 0),
                "volume": q.get("tradeVolume", 0),
                "change": q.get("percentChange", 0)
            }
    except Exception as e:
        print(f"Price error {symbol_token}: {e}")
    return None

# ============ HISTORICAL DATA ============
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
            df = pd.DataFrame(data["data"], columns=["Date", "Open", "High", "Low", "Close", "Volume"])
            df = df.astype({"Open": float, "High": float, "Low": float, "Close": float, "Volume": float})
            return df
    except Exception as e:
        print(f"Historical error {symbol_token}: {e}")
    return pd.DataFrame()

# ============ OPTIONS DATA ============
def get_options_chain(symbol="NIFTY"):
    try:
        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/optionChain"
        payload = {"name": symbol, "expirydate": get_next_expiry()}
        resp = requests.post(url, json=payload, headers=get_angel_headers(), timeout=10)
        data = resp.json()
        if data.get("status") and data.get("data"):
            return data["data"]
        return None
    except Exception as e:
        print(f"Options chain error: {e}")
        return None

def get_next_expiry():
    today = datetime.now()
    days_until_thursday = (3 - today.weekday()) % 7
    if days_until_thursday == 0:
        days_until_thursday = 7
    next_thursday = today + timedelta(days=days_until_thursday)
    return next_thursday.strftime("%d%b%Y").upper()

def get_next_friday_expiry():
    today = datetime.now()
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7
    next_friday = today + timedelta(days=days_until_friday)
    return next_friday.strftime("%d%b%Y").upper()

def get_sensex_options():
    try:
        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/optionChain"
        payload = {"name": "SENSEX", "expirydate": get_next_friday_expiry()}
        resp = requests.post(url, json=payload, headers=get_angel_headers(), timeout=10)
        data = resp.json()
        if data.get("status") and data.get("data"):
            return data["data"]
        return None
    except Exception as e:
        print(f"Sensex options error: {e}")
        return None

def analyze_options_chain(chain_data, spot_price):
    if not chain_data:
        return None
    try:
        total_ce_oi = 0
        total_pe_oi = 0
        strike_data = {}
        for item in chain_data:
            strike = item.get("strikePrice", 0)
            ce_oi = item.get("CE", {}).get("openInterest", 0) or 0
            pe_oi = item.get("PE", {}).get("openInterest", 0) or 0
            ce_price = item.get("CE", {}).get("lastPrice", 0) or 0
            pe_price = item.get("PE", {}).get("lastPrice", 0) or 0
            ce_iv = item.get("CE", {}).get("impliedVolatility", 0) or 0
            pe_iv = item.get("PE", {}).get("impliedVolatility", 0) or 0
            total_ce_oi += ce_oi
            total_pe_oi += pe_oi
            strike_data[strike] = {
                "ce_oi": ce_oi, "pe_oi": pe_oi,
                "ce_price": ce_price, "pe_price": pe_price,
                "ce_iv": ce_iv, "pe_iv": pe_iv,
                "total_oi": ce_oi + pe_oi
            }
        pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0
        pcr_signal = "Bullish" if pcr > 1.2 else "Bearish" if pcr < 0.8 else "Neutral"
        max_pain = calculate_max_pain(strike_data)
        atm = min(strike_data.keys(), key=lambda x: abs(x - spot_price))
        atm_data = strike_data.get(atm, {})
        pe_strikes = sorted(strike_data.items(), key=lambda x: x[1]["pe_oi"], reverse=True)[:3]
        ce_strikes = sorted(strike_data.items(), key=lambda x: x[1]["ce_oi"], reverse=True)[:3]
        atm_ce_iv = atm_data.get("ce_iv", 0)
        atm_pe_iv = atm_data.get("pe_iv", 0)
        avg_iv = round((atm_ce_iv + atm_pe_iv) / 2, 1) if (atm_ce_iv and atm_pe_iv) else 0
        return {
            "pcr": pcr, "pcr_signal": pcr_signal,
            "max_pain": max_pain, "atm_strike": atm,
            "atm_ce_price": atm_data.get("ce_price", 0),
            "atm_pe_price": atm_data.get("pe_price", 0),
            "atm_iv": avg_iv,
            "total_ce_oi": total_ce_oi, "total_pe_oi": total_pe_oi,
            "pe_support": [s[0] for s in pe_strikes],
            "ce_resistance": [s[0] for s in ce_strikes]
        }
    except Exception as e:
        print(f"Options analysis error: {e}")
        return None

def calculate_max_pain(strike_data):
    try:
        strikes = sorted(strike_data.keys())
        min_pain = float("inf")
        max_pain_strike = strikes[0]
        for test_strike in strikes:
            pain = 0
            for strike, data in strike_data.items():
                if test_strike > strike:
                    pain += data["ce_oi"] * (test_strike - strike)
                if test_strike < strike:
                    pain += data["pe_oi"] * (strike - test_strike)
            if pain < min_pain:
                min_pain = pain
                max_pain_strike = test_strike
        return max_pain_strike
    except:
        return "N/A"

def get_stock_options(symbol_name, spot_price):
    try:
        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/optionChain"
        payload = {"name": symbol_name.upper(), "expirydate": get_next_expiry()}
        resp = requests.post(url, json=payload, headers=get_angel_headers(), timeout=10)
        data = resp.json()
        if not data.get("status") or not data.get("data"):
            return None
        chain = data["data"]
        total_ce_oi = 0
        total_pe_oi = 0
        strike_data = {}
        for item in chain:
            strike = item.get("strikePrice", 0)
            ce_oi = item.get("CE", {}).get("openInterest", 0) or 0
            pe_oi = item.get("PE", {}).get("openInterest", 0) or 0
            ce_price = item.get("CE", {}).get("lastPrice", 0) or 0
            pe_price = item.get("PE", {}).get("lastPrice", 0) or 0
            ce_iv = item.get("CE", {}).get("impliedVolatility", 0) or 0
            pe_iv = item.get("PE", {}).get("impliedVolatility", 0) or 0
            total_ce_oi += ce_oi
            total_pe_oi += pe_oi
            strike_data[strike] = {
                "ce_oi": ce_oi, "pe_oi": pe_oi,
                "ce_price": ce_price, "pe_price": pe_price,
                "ce_iv": ce_iv, "pe_iv": pe_iv
            }
        if not strike_data:
            return None
        pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0
        pcr_signal = "Bullish ✅" if pcr > 1.2 else "Bearish ❌" if pcr < 0.8 else "Neutral ⚖️"
        max_pain = calculate_max_pain(strike_data)
        atm = min(strike_data.keys(), key=lambda x: abs(x - spot_price))
        atm_data = strike_data.get(atm, {})
        avg_iv = round((atm_data.get("ce_iv", 0) + atm_data.get("pe_iv", 0)) / 2, 1)
        iv_signal = "High ⚠️" if avg_iv > 30 else "Normal ✅" if avg_iv > 15 else "Low 📉"
        return {
            "pcr": pcr, "pcr_signal": pcr_signal,
            "max_pain": max_pain, "atm_strike": atm,
            "atm_ce": atm_data.get("ce_price", 0),
            "atm_pe": atm_data.get("pe_price", 0),
            "iv": avg_iv, "iv_signal": iv_signal
        }
    except Exception as e:
        print(f"Stock options error {symbol_name}: {e}")
        return None

# ============ OPTIONS STRATEGIES ============
def get_straddle_setup(options_data, spot_price):
    if not options_data:
        return None
    try:
        atm = options_data["atm_strike"]
        ce_price = options_data["atm_ce_price"]
        pe_price = options_data["atm_pe_price"]
        total_premium = round(ce_price + pe_price, 2)
        upper_be = round(atm + total_premium, 2)
        lower_be = round(atm - total_premium, 2)
        iv = options_data["atm_iv"]
        if iv > 20:
            strategy = "SELL Straddle (High IV)"
            action = f"SELL {atm} CE @ {ce_price} + SELL {atm} PE @ {pe_price}"
            logic = "IV zyada hai — theta decay se profit"
        else:
            strategy = "BUY Straddle (Low IV)"
            action = f"BUY {atm} CE @ {ce_price} + BUY {atm} PE @ {pe_price}"
            logic = "IV kam hai — bada move expected"
        return {
            "strategy": strategy, "action": action,
            "total_premium": total_premium,
            "upper_be": upper_be, "lower_be": lower_be,
            "iv": iv, "logic": logic
        }
    except:
        return None

def get_strangle_setup(options_data, spot_price):
    if not options_data:
        return None
    try:
        atm = options_data["atm_strike"]
        return {
            "ce_strike": atm + 100, "pe_strike": atm - 100,
            "logic": f"Sell {atm+100} CE + Sell {atm-100} PE for range-bound market"
        }
    except:
        return None

def get_bull_call_spread(options_data, spot_price):
    if not options_data:
        return None
    try:
        atm = options_data["atm_strike"]
        buy_price = options_data["atm_ce_price"]
        return {
            "buy": f"BUY {atm} CE @ {buy_price}",
            "sell": f"SELL {atm+100} CE",
            "max_profit": 100,
            "max_loss": round(buy_price, 2),
            "logic": "Bullish view with limited risk"
        }
    except:
        return None

def get_bear_put_spread(options_data, spot_price):
    if not options_data:
        return None
    try:
        atm = options_data["atm_strike"]
        buy_price = options_data["atm_pe_price"]
        return {
            "buy": f"BUY {atm} PE @ {buy_price}",
            "sell": f"SELL {atm-100} PE",
            "max_profit": 100,
            "max_loss": round(buy_price, 2),
            "logic": "Bearish view with limited risk"
        }
    except:
        return None

# ============ GLOBAL MARKETS ============
def get_global_markets():
    import yfinance as yf
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

# ============ MACRO DATA ============
def get_macro_data():
    import yfinance as yf
    data = {}
    symbols = {
        "crude": "CL=F", "dollar": "USDINR=X",
        "vix": "^INDIAVIX", "gold": "GC=F",
        "silver": "SI=F", "us10y": "^TNX"
    }
    for key, symbol in symbols.items():
        try:
            t = yf.Ticker(symbol)
            data[key] = round(t.fast_info.last_price, 2)
        except:
            data[key] = "N/A"
    return data

# ============ NEWS ============
def get_fii_dii():
    try:
        feed = feedparser.parse("https://www.moneycontrol.com/rss/fiidiiactivity.xml")
        if feed.entries:
            return feed.entries[0].title
        return "FII/DII unavailable"
    except:
        return "FII/DII unavailable"

def get_news():
    try:
        url = "https://news.google.com/rss/search?q=india+stock+market+nifty&hl=en-IN&gl=IN&ceid=IN:en"
        feed = feedparser.parse(url)
        return [e.title for e in feed.entries[:6]]
    except:
        return ["News unavailable"]

def get_sector_impact(news_list):
    impacted = []
    for news in news_list:
        news_lower = news.lower()
        for kw, sectors in SECTOR_NEWS_MAP.items():
            if kw in news_lower:
                impact = f"{kw.upper()} -> {sectors}"
                if impact not in impacted:
                    impacted.append(impact)
    return impacted[:4] if impacted else ["No major trigger"]

# ============ PRE-OPEN MARKET ============
def get_pre_open_data():
    try:
        gainers = []
        losers = []
        for name, token in list(WATCHLIST.items())[:20]:
            live = get_live_price(token)
            if live and live["ltp"] > 0:
                change = round(float(live["change"]), 2)
                price = round(float(live["ltp"]), 2)
                if change > 0.5:
                    gainers.append((name, price, change))
                elif change < -0.5:
                    losers.append((name, price, change))
            time.sleep(0.2)
        gainers.sort(key=lambda x: x[2], reverse=True)
        losers.sort(key=lambda x: x[2])
        return gainers[:5], losers[:5]
    except Exception as e:
        print(f"Pre-open error: {e}")
        return [], []

# ============ MARKET MOOD METER ============
def get_market_mood(buy_count, sell_count, vix, pcr, fii_dii):
    try:
        score = 50
        # Signal score
        total = buy_count + sell_count
        if total > 0:
            buy_ratio = buy_count / total
            score += (buy_ratio - 0.5) * 30
        # VIX score
        if vix and vix != "N/A":
            if float(vix) < 14:
                score += 10
            elif float(vix) > 20:
                score -= 15
        # PCR score
        if pcr:
            if pcr > 1.2:
                score += 10
            elif pcr < 0.8:
                score -= 10
        score = max(0, min(100, round(score)))
        if score >= 70:
            mood = "BULLISH 🟢"
            advice = "Aggressive trading kar sakte ho ✅"
        elif score >= 55:
            mood = "SLIGHTLY BULLISH 🟡"
            advice = "Selective BUY karo, risk manage karo"
        elif score >= 45:
            mood = "NEUTRAL ⚪"
            advice = "Wait karo, clarity ka intezaar karo"
        elif score >= 30:
            mood = "SLIGHTLY BEARISH 🟠"
            advice = "Cautious raho, SL tight rakho"
        else:
            mood = "BEARISH 🔴"
            advice = "Trading avoid karo ya hedge karo"
        return score, mood, advice
    except:
        return 50, "NEUTRAL ⚪", "Market data check karo"

# ============ SECTOR ROTATION ============
def get_sector_performance(all_signals):
    try:
        sector_data = {}
        signal_map = {s["name"]: s["change"] for s in all_signals}
        for sector, stocks in SECTOR_MAP.items():
            changes = []
            for stock in stocks:
                if stock in signal_map:
                    changes.append(signal_map[stock])
            if changes:
                avg = round(sum(changes) / len(changes), 2)
                sector_data[sector] = avg
        sorted_sectors = sorted(sector_data.items(), key=lambda x: x[1], reverse=True)
        return sorted_sectors
    except:
        return []

# ============ RISK LEVEL ============
def get_risk_level(signal_data, vix, pcr):
    try:
        risk_score = 0
        reasons = []
        # VIX check
        if vix and vix != "N/A":
            if float(vix) < 14:
                reasons.append("VIX kam hai ✅")
            elif float(vix) > 20:
                risk_score += 2
                reasons.append("VIX zyada hai ⚠️")
        # PCR check
        if pcr:
            if pcr > 1.2:
                reasons.append("PCR bullish ✅")
            elif pcr < 0.8:
                risk_score += 1
                reasons.append("PCR bearish ⚠️")
        # Volume check
        if signal_data.get("vol_sig") == "High Vol":
            reasons.append("High volume confirmation ✅")
        else:
            risk_score += 1
        # 52W check
        if "SUPPORT" in str(signal_data.get("w52", "")):
            reasons.append("Near 52W support ✅")
        # RSI check
        if signal_data.get("rsi", 50) < 35:
            reasons.append("RSI extreme oversold ✅")
        if risk_score == 0:
            level = "🟢 LOW RISK"
        elif risk_score == 1:
            level = "🟡 MEDIUM RISK"
        else:
            level = "🔴 HIGH RISK"
        return level, reasons
    except:
        return "⚪ UNKNOWN", []

# ============ TECHNICAL ============
def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    try:
        high = df["High"]
        low = df["Low"]
        close = df["Close"]
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return round(float(tr.rolling(period).mean().iloc[-1]), 2)
    except:
        return None

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
        if lower >= body * 2 and c > o:
            return "Hammer (Bullish)"
        if upper >= body * 2 and c < o:
            return "Shooting Star (Bearish)"
        if c > o and prev_c < prev_o and c > prev_o:
            return "Bullish Engulfing"
        if c < o and prev_c > prev_o and c < prev_o:
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
        r = sorted([h for h in highs if h > price])[:2]
        s = sorted([l for l in lows if l < price], reverse=True)[:2]
        return {
            "s1": round(s[0], 2) if s else "N/A",
            "s2": round(s[1], 2) if len(s) > 1 else "N/A",
            "r1": round(r[0], 2) if r else "N/A",
            "r2": round(r[1], 2) if len(r) > 1 else "N/A"
        }
    except:
        return {"s1": "N/A", "s2": "N/A", "r1": "N/A", "r2": "N/A"}

def check_52w(df, price):
    try:
        h = round(float(df["High"].max()), 2)
        l = round(float(df["Low"].min()), 2)
        if price >= h * 0.98:
            return f"Near 52W High ({h}) BREAKOUT!"
        elif price <= l * 1.02:
            return f"Near 52W Low ({l}) SUPPORT!"
        return f"52W H:{h} L:{l}"
    except:
        return "N/A"

# ============ TOP PICKS ============
def get_top_picks(buy_signals, n=5):
    try:
        scored = []
        for s in buy_signals:
            score = 0
            if s["rsi"] < 35:
                score += 30
            elif s["rsi"] < 45:
                score += 20
            elif s["rsi"] < 50:
                score += 10
            if s["vol_sig"] == "High Vol":
                score += 20
            if s["trend"] == "Bullish":
                score += 15
            if "SUPPORT" in str(s["w52"]):
                score += 20
            elif "BREAKOUT" in str(s["w52"]):
                score += 15
            if "Bullish Engulfing" in str(s["candle"]):
                score += 15
            elif "Hammer" in str(s["candle"]):
                score += 10
            elif "Strong Bullish" in str(s["candle"]):
                score += 10
            score += s["confidence"] * 3
            scored.append({**s, "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:n]
    except:
        return []

def check_entry_confirmation(signal_data):
    try:
        price = signal_data["price"]
        el = signal_data["el"]
        eh = signal_data["eh"]
        if el <= price <= eh:
            return "⚡ ENTRY ZONE ACTIVE — Abhi lo!"
        elif price < el:
            return f"⏳ Wait karo — entry zone: {el}"
        else:
            return f"⚠️ Price upar hai — chase mat karo"
    except:
        return ""

def get_trade_review(buy_signals):
    try:
        review = ""
        for s in buy_signals[:10]:
            price = s["price"]
            t1 = s["t1"]
            sl = s["sl"]
            name = s["name"]
            if price >= t1:
                status = f"✅ T1 HIT! ({t1})"
            elif price <= sl:
                status = f"🔴 SL HIT ({sl})"
            elif price > s["el"]:
                pnl = round(((price - s["el"]) / s["el"]) * 100, 2)
                status = f"🟡 In Trade +{pnl}%"
            else:
                status = f"⏳ Entry nahi mili"
            review += f"{name}: {status}\n"
        return review
    except:
        return "Review unavailable"

# ============ SIGNAL ENGINE ============
def get_signal(token, name):
    try:
        live = get_live_price(token)
        if not live or live["ltp"] == 0:
            return None
        price = round(float(live["ltp"]), 2)
        change = round(float(live["change"]), 2)
        df = get_historical(token)
        if df.empty or len(df) < 20:
            return None
        atr = calculate_atr(df)
        close = df["Close"]
        rsi = round(float(calculate_rsi(close).iloc[-1]), 1)
        sma20 = round(float(close.rolling(20).mean().iloc[-1]), 2)
        sma50 = round(float(close.rolling(50).mean().iloc[-1]), 2) if len(close) >= 50 else sma20
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = round(float((bb_mid + 2 * bb_std).iloc[-1]), 2)
        bb_lower = round(float((bb_mid - 2 * bb_std).iloc[-1]), 2)
        vol = int(live["volume"])
        avg_vol = int(df["Volume"].tail(20).mean())
        vol_sig = "High Vol" if vol > avg_vol * 1.5 else "Normal Vol"
        candle = detect_candle(df)
        sr = get_sr(df, price)
        w52 = check_52w(df, price)

        signal = "HOLD"
        confidence = 5

        if rsi < 35 and price > sma20:
            signal = "BUY"; confidence = 9
        elif rsi < 45 and sma20 > sma50:
            signal = "BUY"; confidence = 8
        elif rsi < 50 and sma20 > sma50 and change > 0:
            signal = "BUY"; confidence = 7
        elif rsi > 75 and price < sma20:
            signal = "SELL"; confidence = 9
        elif rsi > 65 and sma20 < sma50:
            signal = "SELL"; confidence = 8
        elif rsi > 60 and price < sma20 and change < 0:
            signal = "SELL"; confidence = 7

        if signal == "BUY":
            el = round(price * 0.995, 2)
            eh = round(price * 1.005, 2)
            t1 = round(price * 1.02, 2)
            t2 = round(price * 1.04, 2)
            t3 = round(price * 1.06, 2)
            sl = round(price - (atr * 1.5), 2) if atr else round(price * 0.97, 2)
        elif signal == "SELL":
            el = round(price * 0.995, 2)
            eh = round(price * 1.005, 2)
            t1 = round(price * 0.98, 2)
            t2 = round(price * 0.96, 2)
            t3 = round(price * 0.94, 2)
            sl = round(price + (atr * 1.5), 2) if atr else round(price * 1.03, 2)
        else:
            el = eh = t1 = t2 = t3 = sl = price

        risk = abs(price - sl)
        rr1 = round(abs(t1 - price) / risk, 1) if risk > 0 else 0
        rr2 = round(abs(t2 - price) / risk, 1) if risk > 0 else 0
        trend = "Bullish" if sma20 > sma50 else "Bearish"
        rsi_zone = "Oversold" if rsi < 40 else "Overbought" if rsi > 65 else "Neutral"

        return {
            "name": name, "price": price, "change": change,
            "signal": signal, "confidence": confidence,
            "el": el, "eh": eh, "t1": t1, "t2": t2, "t3": t3, "sl": sl,
            "rr1": rr1, "rr2": rr2, "rsi": rsi, "rsi_zone": rsi_zone,
            "trend": trend, "sma20": sma20, "sma50": sma50,
            "bb_upper": bb_upper, "bb_lower": bb_lower,
            "vol_sig": vol_sig, "candle": candle,
            "s1": sr["s1"], "s2": sr["s2"], "r1": sr["r1"], "r2": sr["r2"],
            "w52": w52
        }
    except Exception as e:
        print(f"Signal error {name}: {e}")
        return None

# ============ CHART ============
def generate_chart(df, name, signal_data):
    try:
        df = df.tail(30).copy().reset_index(drop=True)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7),
                                        gridspec_kw={'height_ratios': [3, 1]},
                                        facecolor='#1a1a2e')
        ax1.set_facecolor('#1a1a2e')
        ax2.set_facecolor('#1a1a2e')
        for i, row in df.iterrows():
            color = '#00ff88' if row['Close'] >= row['Open'] else '#ff4444'
            ax1.plot([i, i], [row['Low'], row['High']], color=color, linewidth=0.8)
            ax1.add_patch(plt.Rectangle((i - 0.3, min(row['Open'], row['Close'])),
                          0.6, abs(row['Close'] - row['Open']), color=color, alpha=0.9))
        sma20 = df['Close'].rolling(20).mean()
        sma50 = df['Close'].rolling(50).mean()
        ax1.plot(sma20, color='#ffaa00', linewidth=1.2, label='SMA20', alpha=0.8)
        ax1.plot(sma50, color='#00aaff', linewidth=1.2, label='SMA50', alpha=0.8)
        if signal_data.get('s1') and signal_data['s1'] != 'N/A':
            ax1.axhline(y=signal_data['s1'], color='#00ff88', linestyle='--',
                        linewidth=0.8, alpha=0.7, label=f"Sup {signal_data['s1']}")
        if signal_data.get('r1') and signal_data['r1'] != 'N/A':
            ax1.axhline(y=signal_data['r1'], color='#ff4444', linestyle='--',
                        linewidth=0.8, alpha=0.7, label=f"Res {signal_data['r1']}")
        ax1.axhline(y=signal_data['el'], color='#ffff00', linestyle=':',
                    linewidth=0.8, alpha=0.6, label=f"Entry {signal_data['el']}")
        ax1.set_title(f"{name} — {signal_data['signal']} | RSI: {signal_data['rsi']} | Conf: {signal_data['confidence']}/10",
                      color='white', fontsize=11, pad=8)
        ax1.legend(loc='upper left', fontsize=7, facecolor='#1a1a2e',
                   labelcolor='white', framealpha=0.5)
        ax1.tick_params(colors='white', labelsize=7)
        for spine in ['top', 'right']:
            ax1.spines[spine].set_visible(False)
        for spine in ['bottom', 'left']:
            ax1.spines[spine].set_color('#444')

        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi_line = 100 - (100 / (1 + rs))
        ax2.plot(rsi_line, color='#aa88ff', linewidth=1.2)
        ax2.axhline(y=70, color='#ff4444', linestyle='--', linewidth=0.7, alpha=0.6)
        ax2.axhline(y=30, color='#00ff88', linestyle='--', linewidth=0.7, alpha=0.6)
        ax2.fill_between(range(len(rsi_line)), rsi_line, 50,
                         where=(rsi_line < 30), alpha=0.2, color='#00ff88')
        ax2.fill_between(range(len(rsi_line)), rsi_line, 50,
                         where=(rsi_line > 70), alpha=0.2, color='#ff4444')
        ax2.set_ylim(0, 100)
        ax2.set_ylabel('RSI', color='white', fontsize=8)
        ax2.tick_params(colors='white', labelsize=7)
        for spine in ['top', 'right']:
            ax2.spines[spine].set_visible(False)
        for spine in ['bottom', 'left']:
            ax2.spines[spine].set_color('#444')

        plt.tight_layout(pad=1.5)
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=120, facecolor='#1a1a2e')
        plt.close()
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Chart error {name}: {e}")
        return None

# ============ AI ============
def get_ai_oneliner(name, signal, rsi, trend):
    try:
        prompt = f"Stock: {name}, Signal: {signal}, RSI: {rsi}, Trend: {trend}. Ek line plain Hindi mein (max 10 words). Koi star mat lagao."
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=40
        )
        return resp.choices[0].message.content.strip()
    except:
        return ""

def get_ai_analysis(macro, news, buy_count, sell_count, options_data):
    try:
        pcr = options_data.get("pcr", "N/A") if options_data else "N/A"
        max_pain = options_data.get("max_pain", "N/A") if options_data else "N/A"
        prompt = f"""
Tu expert Indian stock market analyst hai.
Crude: {macro.get('crude')} | VIX: {macro.get('vix')} | USD/INR: {macro.get('dollar')}
PCR: {pcr} | Max Pain: {max_pain}
BUY signals: {buy_count} | SELL signals: {sell_count}
News: {news[:2]}
Plain Hindi mein sirf 3 lines do. Koi star mat lagao:
"""
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120
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

def send_telegram_photo(photo_buf, caption):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        requests.post(url,
                      data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
                      files={"photo": ("chart.png", photo_buf, "image/png")},
                      timeout=15)
    except Exception as e:
        print(f"Photo send error: {e}")

# ============ MAIN ============
def main():
    print("Logging into Angel One...")
    if not angel_login():
        send_telegram("Angel One login failed!")
        return
    print("Login successful!")

    macro = get_macro_data()
    global_mkts = get_global_markets()
    news = get_news()
    sector_impact = get_sector_impact(news)
    fii_dii = get_fii_dii()

    # Session detect
    hour = (datetime.utcnow().hour + 5) % 24
    minute = datetime.utcnow().minute
    ist_time = hour + minute / 60

    if ist_time < 9.25:       # Before 9:15
        session = "PRE_OPEN"
        session_hi = "Pre-Open 9:00 AM"
    elif ist_time < 12:
        session = "MORNING"
        session_hi = "Subah 10:00 AM"
    elif ist_time < 15:
        session = "MIDDAY"
        session_hi = "Dopahar 12:30 PM"
    else:
        session = "CLOSING"
        session_hi = "Shaam 3:15 PM"

    # ====== PRE-OPEN REPORT ======
    if session == "PRE_OPEN":
        gainers, losers = get_pre_open_data()
        nifty_live = get_live_price("99926000")
        sensex_live = get_live_price("99919000")
        nifty_price = round(float(nifty_live["ltp"]), 2) if nifty_live else "N/A"
        nifty_chg = round(float(nifty_live["change"]), 2) if nifty_live else 0
        sensex_price = round(float(sensex_live["ltp"]), 2) if sensex_live else "N/A"
        sensex_chg = round(float(sensex_live["change"]), 2) if sensex_live else 0

        pre_report = "🌅 <b>PRE-OPEN MARKET REPORT</b>\n"
        pre_report += "================================\n\n"
        pre_report += f"<b>Nifty 50:</b> {nifty_price} ({nifty_chg:+.2f}%)\n"
        pre_report += f"<b>Sensex:</b> {sensex_price} ({sensex_chg:+.2f}%)\n\n"

        pre_report += "<b>GLOBAL MARKETS</b>\n"
        for name, val in global_mkts.items():
            pre_report += f"{name}: {val}\n"

        pre_report += "\n<b>MACRO</b>\n"
        pre_report += f"Crude: ${macro.get('crude')} | Gold: ${macro.get('gold')}\n"
        pre_report += f"USD/INR: {macro.get('dollar')} | VIX: {macro.get('vix')}\n\n"

        if gainers:
            pre_report += "<b>🟢 TOP GAINERS (Pre-Open)</b>\n"
            for name, price, chg in gainers:
                pre_report += f"• {name}: {price} (+{chg}%)\n"

        if losers:
            pre_report += "\n<b>🔴 TOP LOSERS (Pre-Open)</b>\n"
            for name, price, chg in losers:
                pre_report += f"• {name}: {price} ({chg}%)\n"

        pre_report += f"\n<b>FII/DII:</b> {fii_dii}\n"
        pre_report += "\n<b>TOP NEWS</b>\n"
        for n in news[:3]:
            pre_report += f"• {n[:80]}\n"

        pre_report += "\n⏰ <i>Market 9:15 AM pe khuleg — signals 10:00 AM pe aayenge</i>"
        send_telegram(pre_report)
        send_telegram(DISCLAIMER)
        print("Pre-open report sent!")
        return

    # ====== REGULAR SESSION ======
    report = f"<b>DalalStreet {session} REPORT</b>\n<b>{session_hi}</b>\n"
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
        report += f"• {s}\n"
    report += "\n<b>TOP NEWS</b>\n"
    for n in news[:3]:
        report += f"• {n[:80]}\n"
    send_telegram(report)

    # ====== OPTIONS DATA ======
    nifty_live = get_live_price("99926000")
    nifty_spot = round(float(nifty_live["ltp"]), 2) if nifty_live else 0
    banknifty_live = get_live_price("99926009")
    banknifty_spot = round(float(banknifty_live["ltp"]), 2) if banknifty_live else 0
    sensex_live = get_live_price("99919000")
    sensex_spot = round(float(sensex_live["ltp"]), 2) if sensex_live else 0

    nifty_options = analyze_options_chain(get_options_chain("NIFTY"), nifty_spot)
    bn_options = analyze_options_chain(get_options_chain("BANKNIFTY"), banknifty_spot)
    sensex_options = analyze_options_chain(get_sensex_options(), sensex_spot)

    options_report = "<b>OPTIONS INTELLIGENCE</b>\n================================\n\n"
    options_report += f"<b>NIFTY</b> Spot: {nifty_spot}\n"
    if nifty_options:
        options_report += f"PCR: {nifty_options['pcr']} ({nifty_options['pcr_signal']})\n"
        options_report += f"Max Pain: {nifty_options['max_pain']}\n"
        options_report += f"ATM Strike: {nifty_options['atm_strike']}\n"
        options_report += f"ATM CE: {nifty_options['atm_ce_price']} | ATM PE: {nifty_options['atm_pe_price']}\n"
        options_report += f"IV: {nifty_options['atm_iv']}%\n"
        options_report += f"CE Resistance: {nifty_options['ce_resistance']}\n"
        options_report += f"PE Support: {nifty_options['pe_support']}\n"
        options_report += f"Total CE OI: {nifty_options['total_ce_oi']:,}\n"
        options_report += f"Total PE OI: {nifty_options['total_pe_oi']:,}\n"
    else:
        options_report += "⚠️ Market hours mein aayega\n"

    options_report += f"\n<b>BANK NIFTY</b> Spot: {banknifty_spot}\n"
    if bn_options:
        options_report += f"PCR: {bn_options['pcr']} ({bn_options['pcr_signal']})\n"
        options_report += f"Max Pain: {bn_options['max_pain']}\n"
        options_report += f"ATM CE: {bn_options['atm_ce_price']} | ATM PE: {bn_options['atm_pe_price']}\n"
        options_report += f"IV: {bn_options['atm_iv']}%\n"

    options_report += f"\n<b>SENSEX</b> Spot: {sensex_spot}\n"
    if sensex_options:
        options_report += f"PCR: {sensex_options['pcr']} ({sensex_options['pcr_signal']})\n"
        options_report += f"Max Pain: {sensex_options['max_pain']}\n"
        options_report += f"ATM CE: {sensex_options['atm_ce_price']} | ATM PE: {sensex_options['atm_pe_price']}\n"
        options_report += f"IV: {sensex_options['atm_iv']}%\n"
    else:
        options_report += "⚠️ Data unavailable\n"
    send_telegram(options_report)

    # ====== OPTIONS STRATEGIES ======
    strategies_report = "<b>OPTIONS STRATEGIES</b>\n================================\n\n"
    if not nifty_options:
        strategies_report += "⚠️ Market hours mein aayega (9:15 AM - 3:30 PM)\n"
    else:
        straddle = get_straddle_setup(nifty_options, nifty_spot)
        if straddle:
            strategies_report += f"<b>STRADDLE — {straddle['strategy']}</b>\n"
            strategies_report += f"Action: {straddle['action']}\n"
            strategies_report += f"Total Premium: {straddle['total_premium']}\n"
            strategies_report += f"Upper BE: {straddle['upper_be']} | Lower BE: {straddle['lower_be']}\n"
            strategies_report += f"IV: {straddle['iv']}% | Logic: {straddle['logic']}\n\n"
        strangle = get_strangle_setup(nifty_options, nifty_spot)
        if strangle:
            strategies_report += f"<b>STRANGLE</b>\n"
            strategies_report += f"CE: {strangle['ce_strike']} | PE: {strangle['pe_strike']}\n"
            strategies_report += f"Logic: {strangle['logic']}\n\n"
        bull_spread = get_bull_call_spread(nifty_options, nifty_spot)
        if bull_spread:
            strategies_report += f"<b>BULL CALL SPREAD</b>\n"
            strategies_report += f"{bull_spread['buy']}\n{bull_spread['sell']}\n"
            strategies_report += f"Max Profit: {bull_spread['max_profit']} pts | Max Loss: {bull_spread['max_loss']}\n"
            strategies_report += f"Logic: {bull_spread['logic']}\n\n"
        bear_spread = get_bear_put_spread(nifty_options, nifty_spot)
        if bear_spread:
            strategies_report += f"<b>BEAR PUT SPREAD</b>\n"
            strategies_report += f"{bear_spread['buy']}\n{bear_spread['sell']}\n"
            strategies_report += f"Max Profit: {bear_spread['max_profit']} pts | Max Loss: {bear_spread['max_loss']}\n"
            strategies_report += f"Logic: {bear_spread['logic']}\n"
    send_telegram(strategies_report)

    # ====== STOCK SIGNALS ======
    print("Fetching stock signals...")
    buy_signals = []
    sell_signals = []
    breakout_alerts = []
    all_signals = []

    for name, token in WATCHLIST.items():
        data = get_signal(token, name)
        if not data:
            continue
        all_signals.append(data)
        if data["w52"] and ("BREAKOUT" in data["w52"] or "SUPPORT" in data["w52"]):
            breakout_alerts.append(f"{name}: {data['w52']}")
        if data["signal"] == "BUY":
            buy_signals.append(data)
        elif data["signal"] == "SELL":
            sell_signals.append(data)
        time.sleep(0.3)

    buy_signals.sort(key=lambda x: x["confidence"], reverse=True)
    sell_signals.sort(key=lambda x: x["confidence"], reverse=True)

    # ====== MARKET MOOD METER ======
    pcr_val = nifty_options["pcr"] if nifty_options else None
    mood_score, mood_text, mood_advice = get_market_mood(
        len(buy_signals), len(sell_signals), macro.get("vix"), pcr_val, fii_dii
    )
    mood_report = "🌡️ <b>MARKET MOOD METER</b>\n================================\n\n"
    mood_report += f"Score: <b>{mood_score}/100</b>\n"
    mood_report += f"Mood: <b>{mood_text}</b>\n"
    mood_report += f"VIX: {macro.get('vix')} | PCR: {pcr_val or 'N/A'}\n"
    mood_report += f"BUY Signals: {len(buy_signals)} | SELL: {len(sell_signals)}\n"
    mood_report += f"\n💡 <b>{mood_advice}</b>"
    send_telegram(mood_report)

    # ====== SECTOR ROTATION ======
    sector_perf = get_sector_performance(all_signals)
    if sector_perf:
        sector_report = "🏭 <b>SECTOR ROTATION</b>\n================================\n\n"
        for sector, avg_chg in sector_perf:
            if avg_chg > 1:
                emoji = "🔥"
            elif avg_chg > 0:
                emoji = "📈"
            elif avg_chg > -1:
                emoji = "😴"
            else:
                emoji = "⚠️"
            sign = "+" if avg_chg >= 0 else ""
            sector_report += f"{emoji} {sector}: {sign}{avg_chg}%\n"
        if sector_perf:
            best = sector_perf[0]
            sector_report += f"\n💡 <b>Focus: {best[0]} stocks aaj strong hain!</b>"
        send_telegram(sector_report)

    # ====== SMART ALERTS ======
    alerts = []
    for s in all_signals:
        if "SUPPORT" in str(s["w52"]) and s["rsi"] < 35 and s["vol_sig"] == "High Vol":
            alerts.append(f"🚨 <b>{s['name']}</b> — 52W Support + RSI {s['rsi']} + High Volume!\n→ Strong bounce possible!")
        elif "BREAKOUT" in str(s["w52"]) and s["vol_sig"] == "High Vol":
            alerts.append(f"🚀 <b>{s['name']}</b> — 52W BREAKOUT + High Volume!\n→ Strong momentum!")
    if alerts:
        alert_report = "🔔 <b>SMART ALERTS</b>\n================================\n\n"
        for a in alerts[:3]:
            alert_report += a + "\n\n"
        send_telegram(alert_report)

    # ====== TOP PICKS + CHARTS ======
    chart_count = 10 if session == "MORNING" else 5
    top_picks = get_top_picks(buy_signals, n=chart_count)

    if top_picks:
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        picks_report = f"🏆 <b>TOP {chart_count} BEST PICKS</b>\n================================\n\n"
        for i, s in enumerate(top_picks):
            entry_status = check_entry_confirmation(s)
            stock_opts = get_stock_options(s['name'], s['price'])
            risk_level, risk_reasons = get_risk_level(s, macro.get("vix"), pcr_val)
            picks_report += f"{medals[i]} <b>{s['name']}</b> — Score: {s['score']}\n"
            picks_report += f"Price: {s['price']} | RSI: {s['rsi']}\n"
            picks_report += f"Entry: {s['el']} - {s['eh']}\n"
            picks_report += f"T1: {s['t1']} | T2: {s['t2']} | SL: {s['sl']}\n"
            picks_report += f"Candle: {s['candle']} | {s['vol_sig']}\n"
            picks_report += f"{entry_status}\n"
            picks_report += f"Risk: {risk_level}\n"
            picks_report += f"{s['w52']}\n"
            if stock_opts:
                picks_report += f"📊 PCR: {stock_opts['pcr']} ({stock_opts['pcr_signal']}) | IV: {stock_opts['iv']}% {stock_opts['iv_signal']}\n"
                picks_report += f"Max Pain: {stock_opts['max_pain']}\n"
            picks_report += "\n"
        send_telegram(picks_report)

        # Charts bhejo
        for s in top_picks:
            token = WATCHLIST.get(s['name'])
            if token:
                df_chart = get_historical(token, days=45)
                if not df_chart.empty:
                    chart_buf = generate_chart(df_chart, s['name'], s)
                    if chart_buf:
                        caption = (f"📈 <b>{s['name']}</b> | {s['signal']} | "
                                   f"RSI: {s['rsi']} | Conf: {s['confidence']}/10\n"
                                   f"Entry: {s['el']}-{s['eh']} | T1: {s['t1']} | SL: {s['sl']}")
                        send_telegram_photo(chart_buf, caption)

    # ====== ALL SIGNALS ======
    signals_report = f"<b>STOCK SIGNALS — BUY:{len(buy_signals)} | SELL:{len(sell_signals)}</b>\n================================\n"
    if breakout_alerts:
        signals_report += "\n<b>52W BREAKOUT ALERTS</b>\n"
        for a in breakout_alerts[:5]:
            signals_report += f"• {a}\n"
    for data in buy_signals[:10]:
        ai = get_ai_oneliner(data["name"], "BUY", data["rsi"], data["trend"])
        stock_opts = get_stock_options(data["name"], data["price"])
        signals_report += f"\n<b>BUY - {data['name']}</b>\n"
        signals_report += f"Price: {data['price']} ({data['change']:+.2f}%)\n"
        signals_report += f"Entry: {data['el']} - {data['eh']}\n"
        signals_report += f"T1: {data['t1']} (R:R 1:{data['rr1']}) | T2: {data['t2']} (R:R 1:{data['rr2']})\n"
        signals_report += f"T3: {data['t3']} | SL: {data['sl']}\n"
        signals_report += f"Support: {data['s1']} / {data['s2']}\n"
        signals_report += f"Resist: {data['r1']} / {data['r2']}\n"
        signals_report += f"BB: {data['bb_lower']} - {data['bb_upper']}\n"
        signals_report += f"RSI: {data['rsi']} ({data['rsi_zone']}) | Trend: {data['trend']}\n"
        signals_report += f"SMA20: {data['sma20']} | SMA50: {data['sma50']}\n"
        signals_report += f"Candle: {data['candle']} | Vol: {data['vol_sig']}\n"
        signals_report += f"{data['w52']}\n"
        signals_report += f"Confidence: {data['confidence']}/10\n"
        if stock_opts:
            signals_report += f"📊 PCR: {stock_opts['pcr']} ({stock_opts['pcr_signal']}) | IV: {stock_opts['iv']}% {stock_opts['iv_signal']}\n"
        if ai:
            signals_report += f"AI: {ai}\n"
        signals_report += "- - - - - - - - -\n"
    for data in sell_signals[:5]:
        ai = get_ai_oneliner(data["name"], "SELL", data["rsi"], data["trend"])
        signals_report += f"\n<b>SELL - {data['name']}</b>\n"
        signals_report += f"Price: {data['price']} ({data['change']:+.2f}%)\n"
        signals_report += f"T1: {data['t1']} | SL: {data['sl']}\n"
        signals_report += f"RSI: {data['rsi']} ({data['rsi_zone']}) | Trend: {data['trend']}\n"
        signals_report += f"Candle: {data['candle']} | {data['w52']}\n"
        signals_report += f"Confidence: {data['confidence']}/10\n"
        if ai:
            signals_report += f"AI: {ai}\n"
        signals_report += "- - - - - - - - -\n"

    if len(signals_report) > 3800:
        cut = signals_report[:3700]
        last_nl = cut.rfind('\n')
        signals_report = signals_report[:last_nl] if last_nl > 3000 else cut
    send_telegram(signals_report)

    # ====== CHARTS FOR ALL SIGNALS ======
    print("Sending charts...")
    for data in buy_signals[:10]:
        token = WATCHLIST.get(data['name'])
        if token:
            df_chart = get_historical(token, days=45)
            if not df_chart.empty:
                chart_buf = generate_chart(df_chart, data['name'], data)
                if chart_buf:
                    caption = (f"📈 <b>{data['name']}</b> | BUY | "
                               f"RSI: {data['rsi']} | Conf: {data['confidence']}/10\n"
                               f"Entry: {data['el']}-{data['eh']} | T1: {data['t1']} | SL: {data['sl']}")
                    send_telegram_photo(chart_buf, caption)
                    time.sleep(1)

    for data in sell_signals[:5]:
        token = WATCHLIST.get(data['name'])
        if token:
            df_chart = get_historical(token, days=45)
            if not df_chart.empty:
                chart_buf = generate_chart(df_chart, data['name'], data)
                if chart_buf:
                    caption = (f"📉 <b>{data['name']}</b> | SELL | "
                               f"RSI: {data['rsi']} | Conf: {data['confidence']}/10\n"
                               f"T1: {data['t1']} | SL: {data['sl']}")
                    send_telegram_photo(chart_buf, caption)
                    time.sleep(1)

    # ====== AI ANALYSIS ======
    ai_text = get_ai_analysis(macro, news, len(buy_signals), len(sell_signals), nifty_options)
    send_telegram("<b>AI ANALYSIS</b>\n" + ai_text)

    # ====== CLOSING REPORTS ======
    if session == "CLOSING":
        # Trade Review
        if buy_signals:
            review_report = "📊 <b>TRADE REVIEW — Aaj Ka Result</b>\n================================\n\n"
            review_report += get_trade_review(buy_signals)
            review_report += "\n<i>Kal ke liye ready raho! 💪</i>"
            send_telegram(review_report)

        # Weekly Summary (Friday only)
        if datetime.now().weekday() == 4:
            weekly = "📅 <b>WEEKLY SUMMARY</b>\n================================\n\n"
            weekly += f"Total BUY signals this run: {len(buy_signals)}\n"
            weekly += f"Total SELL signals this run: {len(sell_signals)}\n"
            if buy_signals:
                best = max(buy_signals, key=lambda x: x["confidence"])
                weekly += f"Best Pick: <b>{best['name']}</b> (Conf: {best['confidence']}/10)\n"
            weekly += f"Market Mood: {mood_text}\n"
            weekly += f"\n<i>Weekend mein apni strategy plan karo! 📋</i>"
            send_telegram(weekly)

    # ====== DISCLAIMER ======
    send_telegram(DISCLAIMER)
    print("Done! All reports sent.")

if __name__ == "__main__":
    main()
def main():
    print("🚀 DalalStreet Bot Started")
    while True:
        try:
            status, message = is_market_open()
            
            if status:
                # Agar market ON hai, tabhi scan karega
                # Yahan aapka angel_login() aur baaki logic aayega
                print(f"✅ {message} Scanning stocks...")
                time.sleep(30 * 60) # 30 min ka break
            else:
                # Agar market OFF hai (Jaise aaj Sunday hai)
                print(f"😴 {message} Agle check ka wait kar raha hoon...")
                time.sleep(3600) # Har 1 ghante mein check karega
                
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(300)
            
