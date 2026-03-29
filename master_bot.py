import os, requests, pandas as pd, numpy as np, feedparser, json, time, pyotp, pytz, threading
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from groq import Groq

# --- CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ANGEL_API_KEY = os.environ.get("ANGEL_API_KEY")
ANGEL_CLIENT_ID = os.environ.get("ANGEL_CLIENT_ID")
ANGEL_PASSWORD = os.environ.get("ANGEL_PASSWORD")
ANGEL_TOTP = os.environ.get("ANGEL_TOTP")

client = Groq(api_key=GROQ_API_KEY)
angel_token = None
last_heartbeat_day = None
last_login_day = None
SENT_NEWS_FILE = "sent_news.json"

WATCHLIST = {
    "Reliance": "2885", "TCS": "11536", "HDFC Bank": "1333", "SBI": "3045", 
    "Tata Motors": "3456", "Zomato": "5097", "IRFC": "543257", "HAL": "541154"
}

# ============ HELPERS ============
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except: pass

def load_memory():
    if os.path.exists(SENT_NEWS_FILE):
        with open(SENT_NEWS_FILE, "r") as f: return json.load(f)
    return []

def save_memory(data):
    with open(SENT_NEWS_FILE, "w") as f: json.dump(data[-100:], f)

def is_market_open():
    now = datetime.now(IST)
    if now.weekday() >= 5: return False
    return 9 <= now.hour < 16

# ============ NEWS ENGINE (Thread 1) ============
def news_engine():
    print("📰 News Engine: LIVE")
    sent_news = load_memory()
    while True:
        try:
            # News 24/7 chalegi par raat ko break legi
            now = datetime.now(IST)
            if 7 <= now.hour < 23: 
                url = "https://news.google.com/rss/search?q=india+stock+market&hl=en-IN"
                feed = feedparser.parse(url)
                for entry in feed.entries[:10]:
                    news_id = entry.title[:80]
                    if news_id not in sent_news:
                        if any(kw in entry.title.lower() for kw in ['rbi', 'crash', 'fed', 'profit', 'results']):
                            msg = f"🔔 <b>MARKET NEWS</b>\n━━━━━━━━━━━━━━\n{entry.title}"
                            send_telegram(msg)
                            sent_news.append(news_id)
                            save_memory(sent_news)
                            time.sleep(10) # Anti-Spam
                time.sleep(600)
            else:
                time.sleep(3600)
        except: time.sleep(60)

# ============ SCANNER ENGINE (Thread 2) ============
def angel_login():
    global angel_token, last_login_day
    try:
        totp = pyotp.TOTP(ANGEL_TOTP).now()
        headers = {"Content-Type": "application/json", "X-UserType": "USER", "X-SourceID": "WEB", "X-PrivateKey": ANGEL_API_KEY}
        payload = {"clientcode": ANGEL_CLIENT_ID, "password": ANGEL_PASSWORD, "totp": totp}
        resp = requests.post("https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByPassword", json=payload, headers=headers)
        if resp.json().get("status"):
            angel_token = resp.json()["data"]["jwtToken"]
            last_login_day = datetime.now(IST).date()
            return True
    except: return False

def scanner_engine():
    print("📈 Scanner Engine: LIVE")
    while True:
        try:
            def scanner_engine():
    print("📈 Scanner Engine: LIVE")
    while True:
        try:
            # --- YAHAN PASTE KAREIN (Try ke thik niche) ---
            global last_heartbeat_day
            now = datetime.now(IST)
            if now.hour == 9 and now.minute == 0 and last_heartbeat_day != now.date():
                heartbeat_msg = (
                    "🌞 <b>Good Morning Bharat!</b>\n\n"
                    "DalalStreet AI is <b>LIVE</b> and scanning.\n"
                    "━━━━━━━━━━━━━━━\n"
                    "✅ News Engine: Active\n"
                    "✅ Scanner: Ready (9:15 AM)\n"
                    "🚀 Aaj discipline ke saath trade karenge!"
                )
                send_telegram(heartbeat_msg)
                last_heartbeat_day = now.date()
            # ---------------------------------------------

            if is_market_open():
                # ... baaki ka purana code ...
                
            if is_market_open():
                if not angel_token or last_login_day != datetime.now(IST).date():
                    angel_login()
                
                for name, token in WATCHLIST.items():
                    # Step 3: Accuracy Filter (Volume Spurt)
                    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote/"
                    payload = {"mode": "FULL", "exchangeTokens": {"NSE": [token]}}
                    headers = {"Authorization": f"Bearer {angel_token}", "Content-Type": "application/json", "X-PrivateKey": ANGEL_API_KEY, "X-SourceID": "WEB", "X-UserType": "USER"}
                    data = requests.post(url, json=payload, headers=headers).json()
                    
                    if data.get("status"):
                        stock = data["data"]["fetched"][0]
                        ltp = float(stock['ltp'])
                        vol = int(stock['tradeVolume'])
                        
                        # Accuracy Logic: $Price > 0$ and $Volume > 1 Million$
                        if vol > 1000000: 
                            msg = f"🚀 <b>ACCURACY SIGNAL: {name}</b>\nPrice: ₹{ltp}\nVol: 🔥 High Burst\n<i>Volume confirm hai, breakout ho sakta hai!</i>"
                            send_telegram(msg)
                    time.sleep(1)
                time.sleep(1800) # 30 min wait
            else:
                time.sleep(3600)
        except: time.sleep(300)

if __name__ == "__main__":
    t1 = threading.Thread(target=news_engine)
    t2 = threading.Thread(target=scanner_engine)
    t1.start()
    t2.start()
                    
