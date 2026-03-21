import os, requests, json, math, numpy as np, pyotp, feedparser
from datetime import datetime

# ================= CONFIG =================
PAPER_MODE = True
CAPITAL = 50000
TRADE_FILE = "trades.json"
AI_FILE = "ai_data.json"

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("CHAT_ID")
API_KEY = os.getenv("ANGEL_API_KEY")
CID = os.getenv("ANGEL_CLIENT_ID")
PWD = os.getenv("ANGEL_PASSWORD")
TOTP_KEY = os.getenv("ANGEL_TOTP")

# ================= TELEGRAM =================
def send(msg):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  json={"chat_id": CHAT, "text": msg})

# ================= LOGIN =================
def login():
    totp = pyotp.TOTP(TOTP_KEY).now()
    url = "https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByPassword"
    headers = {"Content-Type":"application/json","X-PrivateKey":API_KEY}
    payload = {"clientcode":CID,"password":PWD,"totp":totp}
    r = requests.post(url,json=payload,headers=headers).json()
    return r["data"]["jwtToken"] if r.get("status") else None

def headers(jwt):
    return {"Authorization":f"Bearer {jwt}","X-PrivateKey":API_KEY}

def ltp(token, jwt):
    url="https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote/"
    p={"mode":"FULL","exchangeTokens":{"NSE":[token]}}
    r=requests.post(url,json=p,headers=headers(jwt)).json()
    return r["data"]["fetched"][0]["ltp"]

# ================= FII/DII =================
def get_fii_dii():
    try:
        url = "https://www.moneycontrol.com/rss/fiidiiactivity.xml"
        feed = feedparser.parse(url)
        if feed.entries:
            return feed.entries[0].title
        return "FII/DII Data Not Available"
    except:
        return "FII/DII Error"

# ================= WATCHLIST =================
WATCHLIST = {
    "Nifty 50": "99926000","Sensex": "99919000","Bank Nifty": "99926009",
    "HDFC Bank": "1333","ICICI Bank": "4963","SBI": "3045","Axis Bank": "5900","Kotak Bank": "1922",
    "TCS": "11536","Infosys": "1594","HCL Tech": "7229","Wipro": "3787",
    "Reliance": "2885","ONGC": "2475","BPCL": "526","GAIL": "910",
    "Tata Steel": "3499","JSW Steel": "11723","Hindalco": "1363",
    "Maruti": "10999","Tata Motors": "3456","Bajaj Auto": "16669",
    "Sun Pharma": "3351","Dr Reddy": "881","Cipla": "694",
    "HUL": "1394","ITC": "1660","Nestle": "17963",
    "L&T": "11483","NTPC": "11630","Power Grid": "14977"
}

# ================= AI =================
def load_ai():
    if os.path.exists(AI_FILE):
        return json.load(open(AI_FILE))
    return {}

def save_ai(data):
    json.dump(data, open(AI_FILE,"w"), indent=2)

def ai_score(stock):
    ai = load_ai()
    return ai.get(stock, {}).get("score",5)

def update_ai(stock, pnl):
    ai = load_ai()
    if stock not in ai:
        ai[stock]={"score":5}
    ai[stock]["score"] += 1 if pnl>0 else -1
    ai[stock]["score"] = max(1,min(10,ai[stock]["score"]))
    save_ai(ai)

# ================= SIGNAL =================
def signal(price):
    change = np.random.uniform(-2,2)
    if change > 1: return "BUY",8
    if change < -1: return "SELL",8
    return "HOLD",5

# ================= RISK =================
def position_size(price, sl):
    risk = CAPITAL*0.01
    per = abs(price-sl)
    return max(1,int(risk/per)) if per else 1

# ================= TRADE =================
def execute(jwt,name,price,sl,signal):
    qty = position_size(price,sl)

    send(f"{'🧪 PAPER' if PAPER_MODE else '🚀 LIVE'}\n{signal} {name}\nPrice:{price}\nQty:{qty}")

    trade = {"stock":name,"signal":signal,"entry":price,"sl":sl,"qty":qty,"time":str(datetime.now())}
    data = []
    if os.path.exists(TRADE_FILE):
        data=json.load(open(TRADE_FILE))
    data.append(trade)
    json.dump(data, open(TRADE_FILE,"w"), indent=2)

# ================= MAIN =================
def main():
    jwt = login()
    if not jwt:
        send("❌ Login failed")
        return

    nifty = ltp("99926000",jwt)
    bank = ltp("99926009",jwt)
    sensex = ltp("99919000",jwt)

    vix = 18
    view = "BULLISH" if vix<15 else "BEARISH" if vix>20 else "SIDEWAYS"

    fii_dii = get_fii_dii()

    signals=[]

    for name,token in WATCHLIST.items():
        if name in ["Nifty 50","Sensex","Bank Nifty"]:
            continue
        try:
            price = ltp(token,jwt)
            sig,conf = signal(price)

            if sig!="HOLD":
                signals.append({"name":name,"price":price,"signal":sig,"confidence":conf})
        except:
            continue

    signals = sorted(signals,key=lambda x: x["confidence"]+ai_score(x["name"]),reverse=True)

    best = signals[:2]

    msg=f"""📊 MARKET
NIFTY:{nifty}
BANK:{bank}
SENSEX:{sensex}
VIEW:{view}

"""

    for s in best:
        msg+=f"{s['signal']} {s['name']} @ {s['price']}\n"
        execute(jwt,s["name"],s["price"],s["price"]*0.98,s["signal"])

    msg += f"\n📊 FII/DII:\n{fii_dii}"

    send(msg)

if __name__=="__main__":
    main()
