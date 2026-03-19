import os
import requests
import yfinance as yf
from groq import Groq

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
CHAT_ID = os.environ["CHAT_ID"]

client = Groq(api_key=GROQ_API_KEY)

INDICES = {
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "Bank Nifty": "^NSEBANK"
}

WATCHLIST = {
    "Reliance": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Infosys": "INFY.NS",
    "Tata Steel": "TATASTEEL.NS"
}

def get_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.fast_info
        price = round(data.last_price, 2)
        prev = round(data.previous_close, 2)
        change = round(((price - prev) / prev) * 100, 2)
        arrow = "🟢" if change > 0 else "🔴"
        return f"{arrow} ₹{price} ({change:+.2f}%)"
    except:
        return "N/A"

def get_ai_insight(market_data):
    prompt = f"""
Tu ek expert Indian stock market analyst hai.
Aaj ka market data:
{market_data}

Hindi mein 3-4 line ka short market insight do:
- Market ka mood kya hai
- Kaunsa sector strong hai
- Aaj trader ko kya dhyan rakhna chahiye
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300
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
    report = "🌅 <b>DalalStreet Morning Report</b>\n\n"
    
    report += "📊 <b>INDICES</b>\n"
    market_summary = ""
    for name, symbol in INDICES.items():
        price_str = get_price(symbol)
        report += f"• {name}: {price_str}\n"
        market_summary += f"{name}: {price_str}\n"
    
    report += "\n📈 <b>WATCHLIST</b>\n"
    for name, symbol in WATCHLIST.items():
        price_str = get_price(symbol)
        report += f"• {name}: {price_str}\n"
        market_summary += f"{name}: {price_str}\n"
    
    report += "\n🤖 <b>AI INSIGHT</b>\n"
    insight = get_ai_insight(market_summary)
    report += insight
    
    report += "\n\n📌 <i>DalalStreetBOT by @bharathrawat</i>"
    
    send_telegram(report)
    print("Report sent!")

if __name__ == "__main__":
    main()
