import os
import requests
import yfinance as yf
import feedparser
import json
import numpy as np
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
    "Nifty IT": "^CNXIT",
    "Nifty Pharma": "^CNXPHARMA",
    "Nifty Auto": "^CNXAUTO",
    "Nifty Metal": "^CNXMETAL",
    "Nifty Realty": "^CNXREALTY",
    "Nifty FMCG": "^CNXFMCG",

    # === BANKING ===
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "SBI": "SBIN.NS",
    "Kotak Bank": "KOTAKBANK.NS",
    "Axis Bank": "AXISBANK.NS",
    "Bank of Baroda": "BANKBARODA.NS",
    "PNB": "PNB.NS",

    # === FINANCIAL SERVICES / NBFC ===
    "Bajaj Finance": "BAJFINANCE.NS",
    "Bajaj Finserv": "BAJAJFINSV.NS",
    "Muthoot Finance": "MUTHOOTFIN.NS",
    "Shriram Finance": "SHRIRAMFIN.NS",

    # === BROKERS ===
    "Angel One": "ANGELONE.NS",
    "ICICI Securities": "ISEC.NS",
    "Motilal Oswal": "MOTILALOFS.NS",

    # === INSURANCE ===
    "HDFC Life": "HDFCLIFE.NS",
    "SBI Life": "SBILIFE.NS",
    "LIC": "LICI.NS",
    "New India Assurance": "NIACL.NS",

    # === IT SOFTWARE ===
    "TCS": "TCS.NS",
    "Infosys": "INFY.NS",
    "Wipro": "WIPRO.NS",
    "HCL Tech": "HCLTECH.NS",
    "Tech Mahindra": "TECHM.NS",
    "LTIMindtree": "LTIM.NS",

    # === IT HARDWARE ===
    "Dixon Tech": "DIXON.NS",
    "Kaynes Tech": "KAYNES.NS",
    "Tata Elxsi": "TATAELXSI.NS",
    "KPIT Tech": "KPITTECH.NS",

    # === STEEL ===
    "Tata Steel": "TATASTEEL.NS",
    "JSW Steel": "JSWSTEEL.NS",
    "SAIL": "SAIL.NS",

    # === NON-FERROUS METALS ===
    "Hindalco": "HINDALCO.NS",
    "Vedanta": "VEDL.NS",
    "National Aluminium": "NATIONALUM.NS",
    "Hindustan Zinc": "HINDZINC.NS",

    # === FERRO ALLOYS ===
    "MIDHANI": "MIDHANI.NS",
    "Hindustan Copper": "HINDCOPPER.NS",

    # === MINING ===
    "Coal India": "COALINDIA.NS",
    "NMDC": "NMDC.NS",
    "MOIL": "MOIL.NS",

    # === OIL & GAS ===
    "Reliance": "RELIANCE.NS",
    "ONGC": "ONGC.NS",
    "BPCL": "BPCL.NS",
    "IOC": "IOC.NS",
    "HPCL": "HPCL.NS",

    # === REFINERIES ===
    "Chennai Petro": "CHENNPETRO.NS",
    "MRPL": "MRPL.NS",

    # === PETROCHEMICALS ===
    "GAIL": "GAIL.NS",
    "Deepak Nitrite": "DEEPAKNITR.NS",

    # === GAS DISTRIBUTION ===
    "IGL": "IGL.NS",
    "MGL": "MGL.NS",
    "Gujarat Gas": "GUJGASLTD.NS",

    # === EDIBLE OIL ===
    "Adani Wilmar": "AWL.NS",
    "KRBL": "KRBL.NS",
    "Patanjali Foods": "PATANJALIFO.NS",

    # === FERTILIZERS ===
    "Coromandel": "COROMANDEL.NS",
    "Chambal Fertilizers": "CHAMBLFERT.NS",
    "GSFC": "GSFC.NS",
    "RCF": "RCF.NS",

    # === AGRO CHEMICALS ===
    "UPL": "UPL.NS",
    "PI Industries": "PIIND.NS",
    "Rallis India": "RALLIS.NS",

    # === SUGAR ===
    "Balrampur Chini": "BALRAMCHIN.NS",
    "Renuka Sugars": "RENUKA.NS",
    "Triveni Engineering": "TRIVENI.NS",

    # === AUTOMOBILE ===
    "Maruti": "MARUTI.NS",
    "Tata Motors": "TATAMOTORS.NS",
    "Mahindra": "M&M.NS",
    "Bajaj Auto": "BAJAJ-AUTO.NS",
    "Hero MotoCorp": "HEROMOTOCO.NS",
    "TVS Motor": "TVSMOTOR.NS",
    "Eicher Motors": "EICHERMOT.NS",

    # === AUTO PARTS ===
    "Motherson Sumi": "MOTHERSON.NS",
    "Bosch": "BOSCHLTD.NS",
    "Bharat Forge": "BHARATFORG.NS",
    "Minda Industries": "MINDAIND.NS",

    # === CASTINGS & FORGINGS ===
    "Ramkrishna Forgings": "RKFORGE.NS",
    "Electrosteel Cast": "ELECTCAST.NS",

    # === BEARINGS ===
    "Timken India": "TIMKEN.NS",
    "SKF India": "SKFINDIA.NS",
    "Schaeffler": "SCHAEFFLER.NS",

    # === TYRES ===
    "Apollo Tyres": "APOLLOTYRE.NS",
    "MRF": "MRF.NS",
    "CEAT": "CEATLTD.NS",

    # === PHARMA ===
    "Sun Pharma": "SUNPHARMA.NS",
    "Dr Reddy": "DRREDDY.NS",
    "Cipla": "CIPLA.NS",
    "Divis Lab": "DIVISLAB.NS",
    "Lupin": "LUPIN.NS",
    "Biocon": "BIOCON.NS",

    # === HEALTHCARE ===
    "Apollo Hospitals": "APOLLOHOSP.NS",
    "Fortis Healthcare": "FORTIS.NS",
    "Max Healthcare": "MAXHEALTH.NS",

    # === FMCG ===
    "Hindustan Unilever": "HINDUNILVR.NS",
    "ITC": "ITC.NS",
    "Nestle": "NESTLEIND.NS",
    "Britannia": "BRITANNIA.NS",
    "Dabur": "DABUR.NS",
    "Marico": "MARICO.NS",
    "Godrej Consumer": "GODREJCP.NS",

    # === PAINTS ===
    "Asian Paints": "ASIANPAINT.NS",
    "Berger Paints": "BERGEPAINT.NS",
    "Kansai Nerolac": "KANSAINER.NS",

    # === CEMENT ===
    "UltraTech Cement": "ULTRACEMCO.NS",
    "Ambuja Cement": "AMBUJACEM.NS",
    "ACC": "ACC.NS",
    "Shree Cement": "SHREECEM.NS",
    "Dalmia Bharat": "DALBHARAT.NS",

    # === REALTY ===
    "DLF": "DLF.NS",
    "Godrej Properties": "GODREJPROP.NS",
    "Oberoi Realty": "OBEROIRLTY.NS",
    "Prestige Estates": "PRESTIGE.NS",

    # === INFRA DEVELOPERS ===
    "L&T": "LT.NS",
    "IRB Infra": "IRB.NS",
    "Adani Ports": "ADANIPORTS.NS",

    # === CAPITAL GOODS ELECTRICAL ===
    "ABB India": "ABB.NS",
    "Siemens": "SIEMENS.NS",
    "Havells": "HAVELLS.NS",
    "Polycab": "POLYCAB.NS",

    # === CAPITAL GOODS NON-ELECTRICAL ===
    "Thermax": "THERMAX.NS",
    "BHEL": "BHEL.NS",
    "Elecon Engineering": "ELECON.NS",

    # === CABLES ===
    "Polycab India": "POLYCAB.NS",
    "KEI Industries": "KEI.NS",
    "Sterlite Tech": "STLTECH.NS",

    # === POWER ===
    "NTPC": "NTPC.NS",
    "Power Grid": "POWERGRID.NS",
    "Adani Power": "ADANIPOWER.NS",
    "Tata Power": "TATAPOWER.NS",

    # === POWER INFRASTRUCTURE ===
    "CESC": "CESC.NS",
    "Torrent Power": "TORNTPOWER.NS",

    # === AEROSPACE & DEFENCE ===
    "HAL": "HAL.NS",
    "BEL": "BEL.NS",
    "Bharat Dynamics": "BDL.NS",
    "MTAR Tech": "MTARTECH.NS",
    "Paras Defence": "PDSLTD.NS",

    # === AIR TRANSPORT ===
    "IndiGo": "INDIGO.NS",
    "SpiceJet": "SPICEJET.NS",

    # === SHIPPING ===
    "SCI": "SCI.NS",
    "GE Shipping": "GESHIP.NS",

    # === SHIPBUILDING ===
    "Mazagon Dock": "MAZDOCK.NS",
    "GRSE": "GRSE.NS",
    "Cochin Shipyard": "COCHINSHIP.NS",

    # === LOGISTICS ===
    "Delhivery": "DELHIVERY.NS",
    "Blue Dart": "BLUEDART.NS",
    "TCI Express": "TCIEXP.NS",

    # === RAILWAYS ===
    "IRFC": "IRFC.NS",
    "RVNL": "RVNL.NS",
    "IRCTC": "IRCTC.NS",
    "Titagarh Rail": "TITAGARH.NS",

    # === TELECOM SERVICE ===
    "Bharti Airtel": "BHARTIARTL.NS",
    "Vodafone Idea": "IDEA.NS",

    # === TELECOM INFRA ===
    "Indus Towers": "INDUSTOWER.NS",
    "HFCL": "HFCL.NS",

    # === CONSUMER DURABLES ===
    "Voltas": "VOLTAS.NS",
    "Blue Star": "BLUESTARCO.NS",
    "Crompton Greaves": "CROMPTON.NS",
    "Whirlpool": "WHIRLPOOL.NS",

    # === ELECTRONICS ===
    "Amber Enterprises": "AMBER.NS",
    "Syrma SGS": "SYRMA.NS",

    # === JEWELLERY ===
    "Titan": "TITAN.NS",
    "Kalyan Jewellers": "KALYANKJIL.NS",
    "Senco Gold": "SENCO.NS",

    # === RETAIL ===
    "DMart": "DMART.NS",
    "Trent": "TRENT.NS",
    "V-Mart": "VMART.NS",

    # === QSR / HOTELS & RESTAURANTS ===
    "Jubilant FoodWorks": "JUBLFOOD.NS",
    "Westlife Foodworld": "WESTLIFE.NS",
    "IHCL": "INDHOTEL.NS",
    "Lemon Tree": "LEMONTREE.NS",
    "EIH": "EIHOTEL.NS",

    # === MEDIA & ENTERTAINMENT ===
    "ZEEL": "ZEEL.NS",
    "Sun TV": "SUNTV.NS",
    "PVR Inox": "PVRINOX.NS",

    # === E-COMMERCE / AGGREGATOR ===
    "Zomato": "ZOMATO.NS",
    "Nykaa": "FSN.NS",
    "Paytm": "PAYTM.NS",
    "PolicyBazaar": "POLICYBZR.NS",

    # === TEXTILES ===
    "Trident": "TRIDENT.NS",
    "Raymond": "RAYMOND.NS",
    "Vardhman Textiles": "VTL.NS",

    # === PAPER ===
    "JK Paper": "JKPAPER.NS",
    "West Coast Paper": "WESTCOAST.NS",

    # === CHEMICALS ===
    "Pidilite": "PIDILITIND.NS",
    "Aarti Industries": "AARTIIND.NS",
    "Deepak Fertilisers": "DEEPAKFERT.NS",
    "SRF": "SRF.NS",

    # === PLASTIC PRODUCTS ===
    "Supreme Industries": "SUPREMEIND.NS",
    "Astral": "ASTRAL.NS",

    # === GLASS PRODUCTS ===
    "Asahi India Glass": "ASAHIINDIA.NS",
    "Borosil": "BORORENEW.NS",

    # === ALCOHOLIC BEVERAGES ===
    "United Breweries": "UBL.NS",
    "United Spirits": "MCDOWELL-N.NS",
    "Radico Khaitan": "RADICO.NS",

    # === REITs ===
    "Embassy REIT": "EMBASSY.NS",
    "Mindspace REIT": "MINDSPACE.NS",

    # === PACKAGING ===
    "UFlex": "UFLEX.NS",
    "Mold-Tek Pack": "MOLDTKPAC.NS",

    # === DIVERSIFIED ===
    "ITC": "ITC.NS",
    "Godrej Industries": "GODREJIND.NS",
    "Tata Group": "TATACHEM.NS"
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
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 20:
            return None

        df["RSI"] = calculate_rsi(df)
        rsi = round(float(df["RSI"].iloc[-1]), 1)
        df["SMA20"] = df["Close"].rolling(20).mean()
        df["SMA50"] = df["Close"].rolling(50).mean()
        sma20 = float(df["SMA20"].iloc[-1])
        sma50 = float(df["SMA50"].iloc[-1])
        df["BB_mid"] = df["Close"].rolling(20).mean()
        df["BB_std"] = df["Close"].rolling(20).std()
        df["BB_upper"] = df["BB_mid"] + 2 * df["BB_std"]
        df["BB_lower"] = df["BB_mid"] - 2 * df["BB_std"]
        bb_upper = round(float(df["BB_upper"].iloc[-1]), 2)
        bb_lower = round(float(df["BB_lower"].iloc[-1]), 2)
        price = round(float(df["Close"].iloc[-1]), 2)
        prev = round(float(df["Close"].iloc[-2]), 2)
        change = round(((price - prev) / prev) * 100, 2)
        volume = int(df["Volume"].iloc[-1])
        avg_vol = int(df["Volume"].tail(20).mean())
        vol_signal = "High Vol" if volume > avg_vol * 1.5 else "Normal Vol"
        week_high = round(float(df["High"].tail(5).max()), 2)
        week_low = round(float(df["Low"].tail(5).min()), 2)
        candle = detect_candlestick_pattern(df)
        sr = get_support_resistance(df)
        breakout_52w = check_52week_breakout(df, price)
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
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=250
    )
    return response.choices[0].message.content

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
    hour = (datetime.utcnow().hour + 5) % 24
    macro = get_macro_data()
    global_mkts = get_global_markets()
    news = get_news()
    sector_impact = get_sector_impact(news)
    fii_dii = get_fii_dii()
    options = get_options_data()
    earnings = get_earnings_calendar()

    if hour < 12:
        session = "MORNING"
        session_hi = "Subah 9:15 AM"
    elif hour < 15:
        session = "MIDDAY"
        session_hi = "Dopahar 12 PM"
    else:
        session = "CLOSING"
        session_hi = "Shaam 3:30 PM"

    # Pre-market alert
    if hour == 8:
        pre = "<b>PRE-MARKET ALERT 8:30 AM</b>\n================================\n"
        pre += "<b>GIFT NIFTY</b>\n"
        pre += f"Gift Nifty: {global_mkts.get('Gift Nifty')}\n"
        pre += "\n<b>OVERNIGHT GLOBAL</b>\n"
        for name, val in global_mkts.items():
            pre += f"{name}: {val}\n"
        pre += f"\n<b>MACRO</b>\nCrude: ${macro.get('crude')} | Gold: ${macro.get('gold')}\n"
        pre += f"USD/INR: {macro.get('dollar')} | VIX: {macro.get('vix')}\n"
        pre += f"\n<b>OPTIONS</b>\nPCR: {options.get('pcr')} ({options.get('pcr_signal')})\nMax Pain: {options.get('max_pain')}\n"
        pre += "\n<b>EARNINGS THIS WEEK</b>\n"
        for e in earnings:
            pre += f"- {e}\n"
        pre += "\n<b>TOP NEWS</b>\n"
        for n in news[:3]:
            pre += f"- {n[:80]}\n"
        pre += "\n<i>Market 9:15 AM pe open hoga. DYOR.</i>"
        if len(pre) > 4000:
            pre = pre[:3900] + "\n..."
        send_telegram(pre)

    report = f"<b>DalalStreet {session} REPORT</b>\n<b>{session_hi}</b>\n"
    report += "================================\n\n"
    report += "<b>GLOBAL MARKETS</b>\n"
    for name, val in global_mkts.items():
        report += f"{name}: {val}\n"
    report += "\n<b>MACRO DATA</b>\n"
    report += f"Crude: ${macro.get('crude')} | Gold: ${macro.get('gold')}\n"
    report += f"USD/INR: {macro.get('dollar')} | Silver: ${macro.get('silver')}\n"
    report += f"VIX: {macro.get('vix')} | US 10Y: {macro.get('us10y')}%\n"
    report += f"\n<b>OPTIONS</b>\nPCR: {options.get('pcr')} ({options.get('pcr_signal')}) | Max Pain: {options.get('max_pain')}\n"
    report += f"CE OI: {options.get('total_ce_oi')} | PE OI: {options.get('total_pe_oi')}\n"
    report += f"\n<b>FII/DII</b>\n{fii_dii}\n"
    report += "\n<b>EARNINGS THIS WEEK</b>\n"
    for e in earnings:
        report += f"- {e}\n"
    report += "\n<b>NEWS IMPACT</b>\n"
    for s in sector_impact:
        report += f"- {s}\n"
    report += "\n<b>TOP NEWS</b>\n"
    for n in news[:3]:
        report += f"- {n[:80]}\n"

    signals_text = ""
    buy_signals = []
    sell_signals = []
    circuit_alerts = []
    breakout_alerts = []

    for name, symbol in WATCHLIST.items():
        data = get_signal(symbol, name)
        if not data:
            continue
        signals_text += f"{name}:{data['signal']} "
        if data['circuit']:
            circuit_alerts.append(f"{name}: {data['circuit']}")
        if "BREAKOUT" in data['breakout_52w'] or "SUPPORT" in data['breakout_52w']:
            breakout_alerts.append(f"{name}: {data['breakout_52w']}")
        if data['signal'] == "BUY":
            buy_signals.append(data)
        elif data['signal'] == "SELL":
            sell_signals.append(data)

    buy_signals.sort(key=lambda x: x['confidence'], reverse=True)
    sell_signals.sort(key=lambda x: x['confidence'], reverse=True)

    if circuit_alerts:
        report += "\n<b>CIRCUIT ALERTS</b>\n"
        for alert in circuit_alerts:
            report += f"- {alert}\n"

    if breakout_alerts:
        report += "\n<b>52W BREAKOUT ALERTS</b>\n"
        for alert in breakout_alerts[:5]:
            report += f"- {alert}\n"

    report += f"\n<b>SIGNALS — BUY:{len(buy_signals)} | SELL:{len(sell_signals)}</b>\n"
    report += "================================\n"

    for data in buy_signals[:4]:
        ai_line = get_ai_oneliner(data['name'], "BUY", data['rsi'], data['trend'], data['reason'])
        report += f"\n<b>BUY - {data['name']}</b>\n"
        report += f"Price: {data['price']} ({data['change']:+.2f}%)\n"
        report += f"Entry Zone: {data['entry_low']} - {data['entry_high']}\n"
        report += f"T1: {data['target1']} (R:R 1:{data['rr1']}) | T2: {data['target2']} (R:R 1:{data['rr2']})\n"
        report += f"T3: {data['target3']} | SL: {data['stoploss']}\n"
        report += f"Support: {data['support1']} / {data['support2']}\n"
        report += f"Resist: {data['resist1']} / {data['resist2']}\n"
        report += f"BB: {data['bb_lower']} - {data['bb_upper']}\n"
        report += f"RSI: {data['rsi']} ({data['rsi_zone']}) | Trend: {data['trend']}\n"
        report += f"SMA20: {data['sma20']} | SMA50: {data['sma50']}\n"
        report += f"Candle: {data['candle']} | Vol: {data['vol_signal']}\n"
        report += f"52W: {data['breakout_52w']}\n"
        report += f"Confidence: {data['confidence']}/10\n"
        if ai_line:
            report += f"AI: {ai_line}\n"
        report += "- - - - - - - - -\n"

    for data in sell_signals[:2]:
        ai_line = get_ai_oneliner(data['name'], "SELL", data['rsi'], data['trend'], data['reason'])
        report += f"\n<b>SELL - {data['name']}</b>\n"
        report += f"Price: {data['price']} ({data['change']:+.2f}%)\n"
        report += f"Entry Zone: {data['entry_low']} - {data['entry_high']}\n"
        report += f"T1: {data['target1']} (R:R 1:{data['rr1']}) | T2: {data['target2']} (R:R 1:{data['rr2']})\n"
        report += f"T3: {data['target3']} | SL: {data['stoploss']}\n"
        report += f"Support: {data['support1']} / {data['support2']}\n"
        report += f"Resist: {data['resist1']} / {data['resist2']}\n"
        report += f"BB: {data['bb_lower']} - {data['bb_upper']}\n"
        report += f"RSI: {data['rsi']} ({data['rsi_zone']}) | Trend: {data['trend']}\n"
        report += f"SMA20: {data['sma20']} | SMA50: {data['sma50']}\n"
        report += f"Candle: {data['candle']} | Vol: {data['vol_signal']}\n"
        report += f"52W: {data['breakout_52w']}\n"
        report += f"Confidence: {data['confidence']}/10\n"
        if ai_line:
            report += f"AI: {ai_line}\n"
        report += "- - - - - - - - -\n"

    tracker = get_paper_trade_summary()
    if tracker:
        report += "\n<b>PAPER TRADE TRACKER</b>\n"
        report += f"Win: {tracker['win']} | Loss: {tracker['loss']} | Accuracy: {tracker['accuracy']}%\n"
        for r in tracker['results'][-3:]:
            report += f"- {r}\n"

    report += "\n================================\n"
    report += "<b>AI ANALYSIS</b>\n"
    report += get_ai_analysis(macro, global_mkts, news, signals_text, len(buy_signals), len(sell_signals), options)
    report += "\n\n<i>DYOR. Not financial advice.</i>"

    if len(report) > 4000:
        report = report[:3900] + "\n...\n<i>DYOR. Not financial advice.</i>"

    send_telegram(report)
    print("Report sent successfully!")

if __name__ == "__main__":
    main()
