import os, requests, pandas as pd, numpy as np, feedparser, json, time, pyotp, pytz
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
from groq import Groq
from datetime import datetime, timedelta

# --- CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
CHAT_ID = os.environ.get("CHAT_ID")
ANGEL_API_KEY = os.environ.get("ANGEL_API_KEY")
ANGEL_CLIENT_ID = os.environ.get("ANGEL_CLIENT_ID")
ANGEL_PASSWORD = os.environ.get("ANGEL_PASSWORD")
ANGEL_TOTP = os.environ.get("ANGEL_TOTP")

client = Groq(api_key=GROQ_API_KEY)
angel_token = None
last_login_day = None

# --- WATCHLIST ---
WATCHLIST = {
    "Reliance": "2885", "TCS": "11536", "HDFC Bank": "1333", "ICICI Bank": "4963",
    "SBI": "3045", "Axis Bank": "5900", "Kotak Bank": "1922", "Infosys": "1594",
    "Tata Motors": "3456", "ITC": "1660", "L&T": "11483", "Zomato": "5097"
}

# ============ GATEKEEPER (Step 1) ============
def is_market_open():
    now = datetime.now(IST)
    if now.weekday() >= 5: return False, "Weekend: Closed"
    market_start = now.replace(hour=9, minute=0, second=0)
    market_end = now.replace(hour=15, minute=45, second=0)
    if not (market_start <= now <= market_end): return False, "Off-Hours: Closed"
    return True, "Active"

# ============ AUTH & DATA ============
def angel_login():
    global angel_token, last_login_day
    try:
        totp = pyotp.TOTP(ANGEL_TOTP).now()
        headers = {"Content-Type": "application/json", "X-UserType": "USER", "X-SourceID": "WEB", "X-PrivateKey": ANGEL_API_KEY}
        payload = {"clientcode": ANGEL_CLIENT_ID, "password": ANGEL_PASSWORD, "totp": totp}
        resp = requests.post("https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByPassword", json=payload, headers=headers, timeout=10)
        data = resp.json()
        if data.get("status"):
            angel_token = data["data"]["jwtToken"]
            last_login_day = datetime.now(IST).date()
            return True
    except: return False
    return False

def get_live_data(token):
    try:
        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote/"
        payload = {"mode": "FULL", "exchangeTokens": {"NSE": [token]}}
        headers = {"Authorization": f"Bearer {angel_token}", "Content-Type": "application/json", "X-PrivateKey": ANGEL_API_KEY, "X-SourceID": "WEB", "X-UserType": "USER"}
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        return resp.json()["data"]["fetched"][0]
    except: return None

# ============ ACCURACY LOGIC (Step 3) ============
def analyze_stock(name, token):
    data = get_live_data(token)
    if not data: return None
    
    price = float(data['ltp'])
    vol = int(data['tradeVolume'])
    change = float(data['percentChange'])
    
    # Step 3: Volume Filter (Simple example: check if vol is significant)
    # Aap isse 20-day average se bhi compare kar sakte hain
    vol_sig = "High Vol 🔥" if vol > 1000000 else "Normal Vol"
    
    # RSI & SMA Logic (Placeholder for your specific formula)
    rsi = 30 # Example value
    signal = "WAIT"
    conf = 5
    
    if rsi < 35 and vol > 500000: # Volume check integrated
        signal = "BUY"
        conf = 8

    return {
        "name": name, "price": price, "signal": signal, 
        "conf": conf, "vol_sig": vol_sig, "rsi": rsi
    }

def main():
    print("🚀 DalalStreet Master Bot Live")
    while True:
        try:
            active, status_msg = is_market_open()
            if active:
                if angel_token is None or last_login_day != datetime.now(IST).date():
                    angel_login()
                
                print(f"🔍 Scanning Market...")
                for name, token in WATCHLIST.items():
                    res = analyze_stock(name, token)
                    if res and res['signal'] == "BUY":
                        msg = f"🚀 <b>{res['name']} BUY SIGNAL</b>\nPrice: {res['price']}\nVol: {res['vol_sig']}\nConfidence: {res['conf']}/10"
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
                    time.sleep(1) # Rate limit
                
                time.sleep(30 * 60)
            else:
                print(f"😴 {status_msg}. Waiting...")
                time.sleep(3600)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(300)

if __name__ == "__main__":
    main()
                
