import os
import requests
import feedparser
import time
import json
import pytz
from datetime import datetime

# --- CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

ALERT_KEYWORDS = {
    "rbi": {"emoji": "🏦", "impact": "Banks, NBFCs", "priority": "HIGH"},
    "repo rate": {"emoji": "🏦", "impact": "Banks, Realty", "priority": "HIGH"},
    "market crash": {"emoji": "🚨", "impact": "Entire Market", "priority": "CRITICAL"},
    "circuit breaker": {"emoji": "🚨", "impact": "Entire Market", "priority": "CRITICAL"},
    "fii": {"emoji": "💰", "impact": "Market Flow", "priority": "MEDIUM"},
    "quarterly results": {"emoji": "📊", "impact": "Specific Stock", "priority": "HIGH"},
    "fed rate": {"emoji": "🇺🇸", "impact": "IT, Metals", "priority": "HIGH"}
}

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

def is_market_session():
    now = datetime.now(IST)
    if now.weekday() >= 5: return False
    if now.hour < 7 or now.hour >= 22: return False
    return True

def check_news_relevance(title):
    title_lower = title.lower()
    matched = []
    for kw, info in ALERT_KEYWORDS.items():
        if kw in title_lower:
            matched.append((kw, info))
    if not matched: return None, None, None
    
    priority_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    matched.sort(key=lambda x: priority_order.get(x[1]["priority"], 0), reverse=True)
    best = matched[0]
    impacts = " | ".join(list(set([m[1]["impact"] for m in matched])))
    emojis = " ".join(list(set([m[1]["emoji"] for m in matched[:2]])))
    return best[1]["priority"], impacts, emojis

def main():
    print("🚀 News Bot Started...")
    sent_news = []
    while True:
        try:
            if is_market_session():
                source_url = "https://news.google.com/rss/search?q=india+stock+market+nifty+sensex&hl=en-IN&gl=IN&ceid=IN:en"
                feed = feedparser.parse(source_url)
                for entry in feed.entries[:10]:
                    news_id = entry.title[:80]
                    if news_id in sent_news: continue
                    priority, impact, emojis = check_news_relevance(entry.title)
                    if priority:
                        now_str = datetime.now(IST).strftime("%I:%M %p")
                        msg = f"{emojis} <b>{priority} ALERT</b>\n━━━━━━━━━━━━━━\n{entry.title}\n\n📊 <b>Impact:</b> {impact}\n⏰ <b>Time:</b> {now_str}"
                        send_telegram(msg)
                        sent_news.append(news_id)
                        time.sleep(5)
                        if len(sent_news) > 100: sent_news.pop(0)
                time.sleep(600)
            else:
                print("😴 Off-Hours: News paused.")
                time.sleep(3600)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
    
