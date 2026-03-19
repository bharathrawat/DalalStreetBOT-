import os
import requests
import yfinance as yf
import feedparser
from groq import Groq
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
CHAT_ID = os.environ["CHAT_ID"]

client = Groq(api_key=GROQ_API_KEY)

WATCHLIST = {
    "Nifty 50": "^NSEI",
    "Bank Nifty": "^NSEBANK",
    "Reliance": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "SBI": "SBIN.NS",
    "Tata Steel": "TATASTEEL.NS",
    "Infosys": "INFY.NS",
    "ONGC": "ONGC.NS",
    "IndiGo": "INDIGO.NS"
}

SECTOR_NEWS_MAP = {
    "rbi": "Banks,NBFCs",
    "rate": "Banks,Realty",
    "crude": "Aviation,Oil",
    "dollar": "IT,Pharma",
    "inflation": "FMCG,Banks",
    "monsoon": "FMCG,Agro,Sugar",
    "defence": "HAL,BEL",
    "pli": "Electronics,Auto",
    "fed": "IT,Metals"
}

def get_macro_data():
    data = {}
    try:
        crude = yf.Ticker("CL=F")
        data["crude"] = round(crude.fast_info.last_price, 2)
    except:
        data["crude"] = "N/A"
    try:
        dollar = yf.Ticker("USDINR=X")
        data["dollar"] = round(dollar.fast_info.last_price, 2)
    except:
        data["dollar"] = "N/A"
    try:
        vix = yf.Ticker("^INDIAVIX")
        data["vix"] = round(vix.fast_info.last_price, 2)
    except:
        data["vix"] = "N/A"
    try:
        gold = yf.Ticker("GC=F")
        data["gold"] = round(gold.fast_info.last_price, 2)
    except:
        data["gold"] = "N/A"
    return data

def get_news():
    news_list = []
    try:
        url = "https://news.google.com/rss/search?q=india+stock+market+nifty&hl=en-IN&gl=IN&ceid=IN:en"
        feed = feedparser.parse(url)
        for entry in feed.entries[:6]:
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
                impacted.append(f"{keyword} -> {sectors}")
    return impacted if impacted else ["No major sector trigger"]

def calculate_rsi(data, period=14):
    delta = data["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_signal(symbol, name):
    try:
        df = yf.download(symbol, period="3mo", interval="1d", progress=False)
        if df.empty or len(df) < 20:
            return None
        df["RSI"] = calculate_rsi(df)
        rsi = round(float(df["RSI"].iloc[-1]), 1)
        df["SMA20"] = df["Close"].rolling(20).mean()
        df["SMA50"] = df["Close"].rolling(50).mean()
        sma20 = float(df["SMA20"].iloc[-1])
        sma50 = float(df["SMA50"].iloc[-1])
        price = round(float(df["Close"].iloc[-1]), 2)
        prev = round(float(df["Close"].iloc[-2]), 2)
        change = round(((price - prev) / prev) * 100, 2)
        signal = "HOLD"
        confidence = 5
        reason = ""
        if rsi < 45 and price > sma20:
            signal = "BUY"
            confidence = 8
            reason = "RSI oversold + above SMA20"
        elif rsi < 50 and sma20 > sma50:
            signal = "BUY"
            confidence = 7
            reason = "RSI low + bullish trend"
        elif rsi > 60 and price < sma20:
            signal = "SELL"
            confidence = 8
            reason = "RSI overbought + below SMA20"
        elif rsi > 65 and sma20 < sma50:
            signal = "SELL"
            confidence = 7
            reason = "RSI high + bearish trend"
        else:
            signal = "HOLD"
            confidence = 5
            reason = f"RSI neutral {rsi}"
        if signal == "BUY":
            target = round(price * 1.03, 2)
            stoploss = round(price * 0.98, 2)
        elif signal == "SELL":
            target = round(price * 0.97, 2)
            stoploss = round(price * 1.02, 2)
        else:
            target = stoploss = price
        arrow = "up" if change > 0 else "down"
        return {
            "name": name,
            "price": price,
            "change": change,
            "arrow": arrow,
            "signal": signal,
            "confidence": confidence,
            "reason": reason,
            "target": target,
            "stoploss": stoploss,
            "rsi": rsi
        }
    except:
        return None

def get_ai_analysis(macro, news, signals):
    prompt = f"""
Tu expert Indian stock market analyst hai.
Aaj ka data:
Crude Oil: {macro.get('crude')}
USD/INR: {macro.get('dollar')}
India VIX: {macro.get('vix')}
Gold: {macro.get('gold')}
News: {news[:3]}
Signals: {signals}
Hindi mein short analysis do:
1. Market mood kya hai
2. Sabse best opportunity
3. Kya avoid karna hai
4. Risk warning
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )
    return response.choices[0].message.content

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    })

def main():
    macro = get_macro_data()
    news = get_news()
    sector_impact = get_sector_impact(news)
    hour = (datetime.utcnow().hour + 5) % 24
    if hour < 12:
        session = "MORNING"
    elif hour < 15:
        session = "MIDDAY"
    else:
        session = "CLOSING"
    report = f"<b>DalalStreet {session} REPORT</b>\n"
    report += "----------------\n\n"
    report += "<b>MACRO DATA</b>\n"
    report += f"Crude: ${macro.get('crude')}\n"
    report += f"USD/INR: {macro.get('dollar')}\n"
    report += f"VIX: {macro.get('vix')}\n"
    report += f"Gold: ${macro.get('gold')}\n\n"
    report += "<b>NEWS IMPACT</b>\n"
    for s in sector_impact[:3]:
        report += f"- {s}\n"
    report += "\n<b>SIGNALS</b>\n"
    signals_text = ""
    for name, symbol in WATCHLIST.items():
        data = get_signal(symbol, name)
        if not data:
            continue
        signals_text += f"{name}:{data['signal']} "
        if data['signal'] in ["BUY", "SELL"]:
            report += f"\n<b>{data['name']}</b>\n"
            report += f"Price: {data['price']} ({data['change']:+.2f}%)\n"
            report += f"Signal: {data['signal']}\n"
            report += f"Target: {data['target']}\n"
            report += f"SL: {data['stoploss']}\n"
            report += f"Confidence: {data['confidence']}/10\n"
            report += f"Reason: {data['reason']}\n"
    report += "\n----------------\n"
    report += "<b>AI ANALYSIS</b>\n"
    report += get_ai_analysis(macro, news, signals_text)
    report += "\n\n<i>Sirf educational purpose. DYOR.</i>"
    send_telegram(report)
    print("Report sent!")

if __name__ == "__main__":
    main()
        
