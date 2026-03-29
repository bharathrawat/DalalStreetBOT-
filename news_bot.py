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

# ============ NEWS KEYWORDS & IMPACT ============
ALERT_KEYWORDS = {
    [span_0](start_span)"rbi": {"emoji": "🏦", "impact": "Banks, NBFCs", "priority": "HIGH"},[span_0](end_span)
    [span_1](start_span)"repo rate": {"emoji": "🏦", "impact": "Banks, Realty", "priority": "HIGH"},[span_1](end_span)
    [span_2](start_span)"monetary policy": {"emoji": "🏦", "impact": "Banks", "priority": "HIGH"},[span_2](end_span)
    [span_3](start_span)"market crash": {"emoji": "🚨", "impact": "Entire Market", "priority": "CRITICAL"},[span_3](end_span)
    [span_4](start_span)"circuit breaker": {"emoji": "🚨", "impact": "Entire Market", "priority": "CRITICAL"},[span_4](end_span)
    [span_5](start_span)"nifty falls": {"emoji": "📉", "impact": "Entire Market", "priority": "HIGH"},[span_5](end_span)
    [span_6](start_span)"sensex falls": {"emoji": "📉", "impact": "Entire Market", "priority": "HIGH"},[span_6](end_span)
    [span_7](start_span)"fii": {"emoji": "💰", "impact": "Market Flow", "priority": "MEDIUM"},[span_7](end_span)
    [span_8](start_span)"dii": {"emoji": "💰", "impact": "Market Flow", "priority": "MEDIUM"},[span_8](end_span)
    [span_9](start_span)"crude oil": {"emoji": "🛢️", "impact": "Aviation, Paints", "priority": "MEDIUM"},[span_9](end_span)
    [span_10](start_span)"quarterly results": {"emoji": "📊", "impact": "Specific Stock", "priority": "HIGH"},[span_10](end_span)
    [span_11](start_span)"fed rate": {"emoji": "🇺🇸", "impact": "IT, Metals", "priority": "HIGH"},[span_11](end_span)
    [span_12](start_span)"union budget": {"emoji": "📋", "impact": "Entire Market", "priority": "CRITICAL"}[span_12](end_span)
}

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        [span_13](start_span)}, timeout=10)[span_13](end_span)
    except Exception as e:
        print(f"Telegram error: {e}")

def is_market_session():
    """Check if it's a good time to send news"""
    now = datetime.now(IST)
    # Weekend (Sat=5, Sun=6) par news band rakho
    if now.weekday() >= 5:
        return False
    # Raat 10 PM se subah 7 AM tak news band rakho
    if now.hour < 7 or now.hour >= 22:
        return False
    return True

def check_news_relevance(title):
    title_lower = title.lower()
    matched = []
    for keyword, info in ALERT_KEYWORDS.items():
        if keyword in title_lower:
            [span_14](start_span)matched.append((keyword, info))[span_14](end_span)

    if not matched:
        return None, None, None

    # Priority set karna
    [span_15](start_span)priority_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}[span_15](end_span)
    [span_16](start_span)matched.sort(key=lambda x: priority_order.get(x[1]["priority"], 0), reverse=True)[span_16](end_span)

    best = matched[0]
    impacts = " | ".join(list(set([m[1]["impact"] for m in matched])))
    emojis = " ".join(list(set([m[1]["emoji"] for m in matched[:2]])))
    return best[1]["priority"], impacts, emojis

def main():
    print("🚀 DalalStreet News Bot Started!")
    sent_news = [] # Memory-based tracking for cloud platforms like Railway
    
    while True:
        try:
            if is_market_session():
                print(f"[{datetime.now(IST).strftime('%H:%M:%S')}] Checking news...")
                # Google News RSS for Indian Stock Market
                [span_17](start_span)source_url = "https://news.google.com/rss/search?q=india+stock+market+nifty+sensex&hl=en-IN&gl=IN&ceid=IN:en"[span_17](end_span)
                [span_18](start_span)feed = feedparser.parse(source_url)[span_18](end_span)
                
                for entry in feed.entries[:15]:
                    title = entry.get("title", "")
                    news_id = title[:80] # Unique ID for news

                    if news_id in sent_news:
                        continue

                    priority, impact, emojis = check_news_relevance(title)

                    if priority:
                        now_str = datetime.now(IST).strftime("%I:%M %p")
                        msg = (f"{emojis} <b>{priority} MARKET ALERT</b>\n"
                               f"━━━━━━━━━━━━━━━\n\n"
                               f"{title}\n\n"
                               f"📊 <b>Impact:</b> {impact}\n"
                               f"⏰ <b>Time:</b> {now_str}\n\n"
                               [span_19](start_span)f"<i>⚠️ Do Your Own Research</i>")[span_19](end_span)
                        
                        send_telegram(msg)
                        sent_news.append(news_id)
                        
                        # Anti-Spam: Har message ke baad 10 second ka gap
                        time.sleep(10)
                        
                        # Memory clean up (Last 100 news hi yaad rakhega)
                        if len(sent_news) > 100:
                            sent_news.pop(0)

                # Agle full check ke liye 10 min ka wait
                time.sleep(600) 
            else:
                print(f"😴 Off-Hours ({datetime.now(IST).strftime('%H:%M')}): News paused.")
                # Market band hai toh har 1 ghante mein check karo
                time.sleep(3600)
                
        except Exception as e:
            print(f"Main loop error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
