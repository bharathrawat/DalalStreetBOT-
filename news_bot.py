import os
import requests
import feedparser
import time
import json
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# ============ NEWS KEYWORDS & IMPACT ============
ALERT_KEYWORDS = {
    # RBI / Monetary Policy
    "rbi": {"emoji": "🏦", "impact": "Banks, NBFCs, Realty", "priority": "HIGH"},
    "repo rate": {"emoji": "🏦", "impact": "Banks, NBFCs, Realty", "priority": "HIGH"},
    "monetary policy": {"emoji": "🏦", "impact": "Banks, NBFCs", "priority": "HIGH"},
    "interest rate": {"emoji": "🏦", "impact": "Banks, Realty", "priority": "HIGH"},
    "mpc": {"emoji": "🏦", "impact": "Banks, NBFCs", "priority": "HIGH"},

    # Market Crash / Circuit
    "circuit breaker": {"emoji": "🚨", "impact": "Entire Market", "priority": "CRITICAL"},
    "market crash": {"emoji": "🚨", "impact": "Entire Market", "priority": "CRITICAL"},
    "sensex crash": {"emoji": "🚨", "impact": "Entire Market", "priority": "CRITICAL"},
    "nifty crash": {"emoji": "🚨", "impact": "Entire Market", "priority": "CRITICAL"},
    "lower circuit": {"emoji": "🔴", "impact": "Specific Stock", "priority": "HIGH"},
    "upper circuit": {"emoji": "🟢", "impact": "Specific Stock", "priority": "HIGH"},
    "market halt": {"emoji": "🚨", "impact": "Entire Market", "priority": "CRITICAL"},
    "sensex falls": {"emoji": "📉", "impact": "Entire Market", "priority": "HIGH"},
    "nifty falls": {"emoji": "📉", "impact": "Entire Market", "priority": "HIGH"},
    "sell off": {"emoji": "📉", "impact": "Entire Market", "priority": "HIGH"},

    # FII/DII
    "fii": {"emoji": "💰", "impact": "Entire Market", "priority": "MEDIUM"},
    "foreign investors": {"emoji": "💰", "impact": "Entire Market", "priority": "MEDIUM"},
    "fpi": {"emoji": "💰", "impact": "Entire Market", "priority": "MEDIUM"},
    "dii": {"emoji": "💰", "impact": "Entire Market", "priority": "MEDIUM"},
    "institutional buying": {"emoji": "🟢", "impact": "Entire Market", "priority": "MEDIUM"},
    "institutional selling": {"emoji": "🔴", "impact": "Entire Market", "priority": "MEDIUM"},

    # Crude Oil / Gold
    "crude oil": {"emoji": "🛢️", "impact": "Aviation, Oil, Paints", "priority": "MEDIUM"},
    "crude rises": {"emoji": "🛢️", "impact": "Aviation, Oil, Paints", "priority": "MEDIUM"},
    "crude falls": {"emoji": "🛢️", "impact": "Aviation, Oil, Paints", "priority": "MEDIUM"},
    "brent crude": {"emoji": "🛢️", "impact": "Aviation, Oil, Paints", "priority": "MEDIUM"},
    "gold price": {"emoji": "🥇", "impact": "Gold ETFs, Jewellery", "priority": "MEDIUM"},
    "gold rises": {"emoji": "🥇", "impact": "Gold ETFs, Jewellery", "priority": "MEDIUM"},
    "gold falls": {"emoji": "🥇", "impact": "Gold ETFs, Jewellery", "priority": "MEDIUM"},
    "silver price": {"emoji": "🥈", "impact": "Silver ETFs", "priority": "LOW"},

    # Budget / Government Policy
    "union budget": {"emoji": "📋", "impact": "Entire Market", "priority": "CRITICAL"},
    "budget 2025": {"emoji": "📋", "impact": "Entire Market", "priority": "CRITICAL"},
    "budget 2026": {"emoji": "📋", "impact": "Entire Market", "priority": "CRITICAL"},
    "government policy": {"emoji": "🏛️", "impact": "Sector Specific", "priority": "HIGH"},
    "sebi": {"emoji": "⚖️", "impact": "Market Regulation", "priority": "HIGH"},
    "gst": {"emoji": "📋", "impact": "FMCG, Auto, Realty", "priority": "HIGH"},
    "tax": {"emoji": "📋", "impact": "Sector Specific", "priority": "MEDIUM"},
    "pli scheme": {"emoji": "🏭", "impact": "Electronics, Auto, Pharma", "priority": "HIGH"},
    "infrastructure": {"emoji": "🏗️", "impact": "Infra, Cement, Steel", "priority": "MEDIUM"},

    # Company Results
    "quarterly results": {"emoji": "📊", "impact": "Specific Company", "priority": "HIGH"},
    "q1 results": {"emoji": "📊", "impact": "Specific Company", "priority": "HIGH"},
    "q2 results": {"emoji": "📊", "impact": "Specific Company", "priority": "HIGH"},
    "q3 results": {"emoji": "📊", "impact": "Specific Company", "priority": "HIGH"},
    "q4 results": {"emoji": "📊", "impact": "Specific Company", "priority": "HIGH"},
    "profit rises": {"emoji": "🟢", "impact": "Specific Company", "priority": "HIGH"},
    "profit falls": {"emoji": "🔴", "impact": "Specific Company", "priority": "HIGH"},
    "revenue growth": {"emoji": "📈", "impact": "Specific Company", "priority": "MEDIUM"},
    "earnings": {"emoji": "📊", "impact": "Specific Company", "priority": "MEDIUM"},
    "dividend": {"emoji": "💵", "impact": "Specific Company", "priority": "MEDIUM"},
    "bonus share": {"emoji": "🎁", "impact": "Specific Company", "priority": "HIGH"},
    "stock split": {"emoji": "✂️", "impact": "Specific Company", "priority": "HIGH"},

    # Global Events
    "fed rate": {"emoji": "🇺🇸", "impact": "IT, Metals, Market", "priority": "HIGH"},
    "federal reserve": {"emoji": "🇺🇸", "impact": "IT, Metals, Market", "priority": "HIGH"},
    "us inflation": {"emoji": "🇺🇸", "impact": "IT, Metals", "priority": "HIGH"},
    "ukraine": {"emoji": "⚠️", "impact": "Metals, Oil", "priority": "HIGH"},
    "middle east": {"emoji": "⚠️", "impact": "Oil, Aviation", "priority": "HIGH"},
    "china": {"emoji": "🇨🇳", "impact": "Metals, IT", "priority": "MEDIUM"},
    "dollar": {"emoji": "💵", "impact": "IT, Pharma", "priority": "MEDIUM"},
    "rupee": {"emoji": "₹", "impact": "IT, Pharma, Oil", "priority": "MEDIUM"},
}

NEWS_SOURCES = [
    "https://news.google.com/rss/search?q=india+stock+market+nifty+sensex&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=RBI+repo+rate+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=FII+DII+india+stock&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=crude+oil+gold+price+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=india+budget+government+policy+sebi&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=nifty+sensex+quarterly+results+earnings&hl=en-IN&gl=IN&ceid=IN:en",
]

# Track sent news to avoid duplicates
SENT_NEWS_FILE = "sent_news.json"

def load_sent_news():
    try:
        with open(SENT_NEWS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_sent_news(sent_list):
    try:
        # Keep only last 500 news items
        if len(sent_list) > 500:
            sent_list = sent_list[-500:]
        with open(SENT_NEWS_FILE, "w") as f:
            json.dump(sent_list, f)
    except:
        pass

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def check_news_relevance(title):
    title_lower = title.lower()
    matched = []
    for keyword, info in ALERT_KEYWORDS.items():
        if keyword in title_lower:
            matched.append((keyword, info))

    if not matched:
        return None, None, None

    # Get highest priority match
    priority_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    matched.sort(key=lambda x: priority_order.get(x[1]["priority"], 0), reverse=True)

    best = matched[0]
    keyword, info = best

    # Combine all impacts
    all_impacts = list(set([m[1]["impact"] for m in matched]))
    all_emojis = list(set([m[1]["emoji"] for m in matched[:2]]))

    return info["priority"], " | ".join(all_impacts), " ".join(all_emojis)

def format_alert(title, priority, impact, emojis, source_time):
    now = datetime.now(IST).strftime("%I:%M %p")

    if priority == "CRITICAL":
        header = "🚨 <b>CRITICAL MARKET ALERT</b> 🚨"
        border = "━━━━━━━━━━━━━━━━━━━━━━"
    elif priority == "HIGH":
        header = "⚡ <b>BREAKING NEWS ALERT</b>"
        border = "━━━━━━━━━━━━━━━━━━━━"
    elif priority == "MEDIUM":
        header = f"{emojis} <b>MARKET NEWS</b>"
        border = "──────────────────────"
    else:
        header = f"{emojis} <b>NEWS UPDATE</b>"
        border = "──────────────────────"

    msg = f"{header}\n{border}\n\n"
    msg += f"{emojis} {title}\n\n"
    msg += f"📊 <b>Impact:</b> {impact}\n"
    msg += f"⏰ <b>Time:</b> {now}\n"
    msg += f"\n<i>⚠️ Do Your Own Research</i>"

    return msg

def fetch_and_alert():
    sent_news = load_sent_news()
    new_alerts = 0

    for source_url in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source_url)
            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                link = entry.get("link", "")

                # Create unique ID
                news_id = title[:80]

                # Skip if already sent
                if news_id in sent_news:
                    continue

                # Check relevance
                priority, impact, emojis = check_news_relevance(title)

                if priority:
                    # Format and send alert
                    alert_msg = format_alert(title, priority, impact, emojis, "")
                    send_telegram(alert_msg)
                    sent_news.append(news_id)
                    new_alerts += 1
                    print(f"Alert sent: {title[:60]}")
                    time.sleep(2)  # Avoid spam

        except Exception as e:
            print(f"Feed error {source_url[:50]}: {e}")

    save_sent_news(sent_news)
    return new_alerts

def main():
    print("🚀 DalalStreet News Bot Started!")
    print("Checking news every 15 minutes — 24/7")
    send_telegram(
        "🤖 <b>DalalStreet News Bot — LIVE!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Ab milenge real-time alerts:\n"
        "🏦 RBI / Repo Rate\n"
        "💰 FII/DII Activity\n"
        "🛢️ Crude Oil / Gold\n"
        "🚨 Market Crash / Circuit\n"
        "📋 Budget / Government Policy\n"
        "📊 Company Results\n\n"
        "⏰ Har 15 minute mein news check hogi!\n"
        "<i>⚠️ Do Your Own Research</i>"
    )

    while True:
        try:
            print(f"\n[{datetime.now(IST).strftime('%H:%M:%S')}] Checking news...")
            alerts = fetch_and_alert()
            print(f"Sent {alerts} new alerts")
        except Exception as e:
            print(f"Main loop error: {e}")

        # Wait 15 minutes
        time.sleep(15 * 60)

if __name__ == "__main__":
    main()
