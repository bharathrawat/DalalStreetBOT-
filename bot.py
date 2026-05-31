"""
=============================================================
  MARK MINERVINI STRATEGY - INDIAN STOCK MARKET TELEGRAM BOT
  Based on: SEPA (Specific Entry Point Analysis)
  Strategy: Stage 2 Uptrend + VCP + Relative Strength
=============================================================
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Nifty 50 + Nifty Next 50 popular stocks
WATCHLIST = [
    # Nifty 50
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
    "ICICIBANK.NS", "KOTAKBANK.NS", "BAJFINANCE.NS", "SBIN.NS", "BHARTIARTL.NS",
    "ITC.NS", "ASIANPAINT.NS", "AXISBANK.NS", "LT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS", "ULTRACEMCO.NS", "ONGC.NS",
    "POWERGRID.NS", "NTPC.NS", "M&M.NS", "TECHM.NS", "TATASTEEL.NS",
    "HCLTECH.NS", "JSWSTEEL.NS", "BAJAJFINSV.NS", "ADANIENT.NS", "ADANIPORTS.NS",
    # Mid caps
    "PIDILITIND.NS", "DIVI.NS", "SIEMENS.NS", "HAVELLS.NS", "VOLTAS.NS",
    "PAGEIND.NS", "BERGEPAINT.NS", "MUTHOOTFIN.NS", "TORNTPHARM.NS", "ABBOTINDIA.NS",
    "CHOLAFIN.NS", "COFORGE.NS", "PERSISTENT.NS", "TATAELXSI.NS", "DIXON.NS",
    "ASTRAL.NS", "POLYCAB.NS", "LTTS.NS", "CAMS.NS", "IRCTC.NS"
]

BENCHMARK = "^NSEI"  # Nifty 50

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# MINERVINI STRATEGY ENGINE
# ─────────────────────────────────────────────

class MinerviniAnalyzer:
    """
    Mark Minervini's SEPA Criteria:
    1. Price > 150 MA & 200 MA
    2. 150 MA > 200 MA
    3. 200 MA trending up (at least 1 month)
    4. 50 MA > 150 MA & 200 MA
    5. Price > 50 MA
    6. Price at least 25% above 52-week low
    7. Price within 25% of 52-week high
    8. RS Rating > 70 (relative to Nifty)
    """

    def __init__(self):
        self.benchmark_data = None

    def fetch_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            if df.empty or len(df) < 50:
                return None
            return df
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None

    def fetch_benchmark(self) -> pd.DataFrame:
        if self.benchmark_data is None:
            self.benchmark_data = self.fetch_data(BENCHMARK)
        return self.benchmark_data

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['MA50']  = df['Close'].rolling(50).mean()
        df['MA150'] = df['Close'].rolling(150).mean()
        df['MA200'] = df['Close'].rolling(200).mean()

        # 200 MA slope (compare with 20 bars ago)
        df['MA200_slope'] = df['MA200'] - df['MA200'].shift(20)

        # 52-week high/low
        df['52W_High'] = df['Close'].rolling(252).max()
        df['52W_Low']  = df['Close'].rolling(252).min()

        # ATR for volatility
        df['TR'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low']  - df['Close'].shift(1))
            )
        )
        df['ATR14'] = df['TR'].rolling(14).mean()

        # Volume MA
        df['VolMA20'] = df['Volume'].rolling(20).mean()

        return df

    def check_minervini_criteria(self, df: pd.DataFrame) -> dict:
        latest = df.iloc[-1]
        price  = latest['Close']

        criteria = {
            'C1_price_above_150_200': (price > latest['MA150']) and (price > latest['MA200']),
            'C2_150_above_200':       latest['MA150'] > latest['MA200'],
            'C3_200_trending_up':     latest['MA200_slope'] > 0,
            'C4_50_above_150_200':   (latest['MA50'] > latest['MA150']) and (latest['MA50'] > latest['MA200']),
            'C5_price_above_50':      price > latest['MA50'],
            'C6_25pct_above_52wk_low': price >= latest['52W_Low'] * 1.25,
            'C7_within_25pct_of_high': price >= latest['52W_High'] * 0.75,
        }

        passed = sum(criteria.values())
        total  = len(criteria)

        return {
            'criteria': criteria,
            'passed':   passed,
            'total':    total,
            'stage2':   passed >= 6,   # At least 6/7 = Stage 2
            'score':    round(passed / total * 100, 1)
        }

    def calculate_rs_rating(self, symbol_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> float:
        """Relative Strength vs Nifty (like IBD RS Rating, 1-99)"""
        try:
            sym_ret  = symbol_df['Close'].pct_change().dropna()
            bmk_ret  = benchmark_df['Close'].pct_change().dropna()

            # Align dates
            common = sym_ret.index.intersection(bmk_ret.index)
            if len(common) < 20:
                return 50.0

            sym_ret = sym_ret[common]
            bmk_ret = bmk_ret[common]

            # Weighted RS: 40% last quarter + 20% each prior 3 quarters
            def period_return(series, days):
                if len(series) < days:
                    return 0
                return (series.iloc[-1] / series.iloc[-days] - 1) if series.iloc[-days] != 0 else 0

            sym_rs = (0.4 * period_return(symbol_df['Close'], 63) +
                      0.2 * period_return(symbol_df['Close'], 126) +
                      0.2 * period_return(symbol_df['Close'], 189) +
                      0.2 * period_return(symbol_df['Close'], 252))

            bmk_rs = (0.4 * period_return(benchmark_df['Close'], 63) +
                      0.2 * period_return(benchmark_df['Close'], 126) +
                      0.2 * period_return(benchmark_df['Close'], 189) +
                      0.2 * period_return(benchmark_df['Close'], 252))

            # Normalize to 1-99
            relative = sym_rs - bmk_rs
            # Simple scaling: > +30% = 99, < -30% = 1
            rs = 50 + (relative / 0.30) * 49
            return round(max(1, min(99, rs)), 1)

        except Exception:
            return 50.0

    def detect_vcp(self, df: pd.DataFrame) -> dict:
        """
        VCP (Volatility Contraction Pattern) Detection
        - Multiple contractions in price range
        - Each contraction smaller than previous
        - Volume drying up on contractions
        """
        recent = df.tail(60).copy()

        # Find swing highs and lows
        highs  = recent['High'].values
        lows   = recent['Low'].values
        closes = recent['Close'].values
        vols   = recent['Volume'].values

        # Calculate rolling volatility contractions
        vol_20 = recent['Close'].rolling(20).std()
        vol_10 = recent['Close'].rolling(10).std()
        vol_5  = recent['Close'].rolling(5).std()

        # Check if volatility is contracting
        last_vol20 = vol_20.iloc[-20]
        last_vol10 = vol_10.iloc[-10]
        last_vol5  = vol_5.iloc[-5]

        contraction = (last_vol5 < last_vol10 < last_vol20) if not any(
            pd.isna([last_vol5, last_vol10, last_vol20])) else False

        # Pivot point (potential breakout level)
        pivot = recent['High'].tail(10).max()

        # Volume on contractions vs expansions
        avg_vol = recent['Volume'].mean()
        recent_vol = recent['Volume'].tail(5).mean()
        vol_dry = recent_vol < avg_vol * 0.7

        # Count tight weeks (range < 3%)
        recent['weekly_range'] = (recent['High'] - recent['Low']) / recent['Close']
        tight_bars = (recent['weekly_range'].tail(10) < 0.03).sum()

        return {
            'vcp_forming':  contraction and vol_dry,
            'pivot':        round(pivot, 2),
            'vol_drying':   vol_dry,
            'contraction':  contraction,
            'tight_bars':   int(tight_bars),
        }

    def calculate_entry_exit(self, df: pd.DataFrame, vcp: dict) -> dict:
        latest  = df.iloc[-1]
        price   = latest['Close']
        atr     = latest['ATR14']

        # Entry: 1% above pivot (Minervini style)
        entry = round(vcp['pivot'] * 1.01, 2)

        # Stop loss: just below pivot or recent low (2x ATR)
        stop = round(min(vcp['pivot'] * 0.96, price - 2 * atr), 2)

        # Targets based on R:R
        risk    = entry - stop
        target1 = round(entry + 2 * risk, 2)   # 2:1 R:R
        target2 = round(entry + 3 * risk, 2)   # 3:1 R:R

        # Position size for 1% portfolio risk (assuming 10L portfolio)
        portfolio = 1_000_000
        risk_per_trade = portfolio * 0.01
        shares = int(risk_per_trade / (entry - stop)) if (entry - stop) > 0 else 0

        return {
            'current_price': round(price, 2),
            'entry':         entry,
            'stop':          stop,
            'target1':       target1,
            'target2':       target2,
            'risk_reward':   round((target1 - entry) / (entry - stop), 2) if (entry - stop) > 0 else 0,
            'suggested_qty': shares,
            'atr':           round(atr, 2),
        }

    def full_analysis(self, symbol: str) -> dict:
        """Complete Minervini analysis for a stock"""
        df = self.fetch_data(symbol, period="2y")
        if df is None:
            return None

        df = self.calculate_indicators(df)

        if df.iloc[-1][['MA50', 'MA150', 'MA200']].isna().any():
            return None

        benchmark = self.fetch_benchmark()
        criteria  = self.check_minervini_criteria(df)
        rs_rating = self.calculate_rs_rating(df, benchmark) if benchmark is not None else 50
        vcp       = self.detect_vcp(df)
        trade     = self.calculate_entry_exit(df, vcp)

        # Overall signal
        if criteria['stage2'] and rs_rating >= 70 and vcp['vcp_forming']:
            signal = "🟢 STRONG BUY"
        elif criteria['stage2'] and rs_rating >= 60:
            signal = "🟡 WATCH"
        elif criteria['score'] >= 50:
            signal = "⚪ NEUTRAL"
        else:
            signal = "🔴 AVOID"

        return {
            'symbol':    symbol.replace('.NS', ''),
            'signal':    signal,
            'criteria':  criteria,
            'rs_rating': rs_rating,
            'vcp':       vcp,
            'trade':     trade,
            'df':        df,
        }


# ─────────────────────────────────────────────
# CHART GENERATOR
# ─────────────────────────────────────────────

def generate_chart(symbol: str, df: pd.DataFrame, trade: dict) -> BytesIO:
    """Generate Minervini-style price chart with MAs"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8),
                                    gridspec_kw={'height_ratios': [3, 1]},
                                    facecolor='#0d1117')

    recent = df.tail(120)
    dates  = range(len(recent))

    # ── Price & MAs ──
    ax1.set_facecolor('#0d1117')
    ax1.plot(dates, recent['Close'],  color='#e6edf3', linewidth=1.5, label='Price',  zorder=5)
    ax1.plot(dates, recent['MA50'],   color='#f78166', linewidth=1.2, label='MA50',   zorder=4)
    ax1.plot(dates, recent['MA150'],  color='#ffa657', linewidth=1.2, label='MA150',  zorder=3)
    ax1.plot(dates, recent['MA200'],  color='#3fb950', linewidth=1.5, label='MA200',  zorder=3)

    # Entry / Stop lines
    ax1.axhline(trade['entry'],  color='#58a6ff', linestyle='--', linewidth=1.2, label=f"Entry ₹{trade['entry']}")
    ax1.axhline(trade['stop'],   color='#f85149', linestyle='--', linewidth=1.2, label=f"Stop ₹{trade['stop']}")
    ax1.axhline(trade['target1'],color='#3fb950', linestyle=':',  linewidth=1.2, label=f"T1 ₹{trade['target1']}")

    ax1.set_title(f"  {symbol.replace('.NS','')}  —  Minervini SEPA Analysis",
                  color='#e6edf3', fontsize=14, fontweight='bold', pad=10, loc='left')
    ax1.legend(loc='upper left', fontsize=8, facecolor='#161b22',
               edgecolor='#30363d', labelcolor='#e6edf3')
    ax1.tick_params(colors='#8b949e')
    ax1.spines[:].set_color('#30363d')
    ax1.yaxis.label.set_color('#8b949e')
    ax1.set_ylabel('Price (₹)', color='#8b949e')

    # Fill above/below MA200
    ax1.fill_between(dates, recent['Close'], recent['MA200'],
                     where=recent['Close'] >= recent['MA200'],
                     alpha=0.08, color='#3fb950')
    ax1.fill_between(dates, recent['Close'], recent['MA200'],
                     where=recent['Close'] < recent['MA200'],
                     alpha=0.08, color='#f85149')

    # ── Volume ──
    ax2.set_facecolor('#0d1117')
    colors = ['#3fb950' if c >= o else '#f85149'
              for c, o in zip(recent['Close'], recent['Open'])]
    ax2.bar(dates, recent['Volume'], color=colors, alpha=0.7, width=0.8)
    ax2.plot(dates, recent['VolMA20'], color='#ffa657', linewidth=1, label='Vol MA20')
    ax2.set_ylabel('Volume', color='#8b949e', fontsize=8)
    ax2.tick_params(colors='#8b949e', labelsize=7)
    ax2.spines[:].set_color('#30363d')

    plt.tight_layout(pad=1.5)

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='#0d1117')
    buf.seek(0)
    plt.close()
    return buf


# ─────────────────────────────────────────────
# TELEGRAM BOT HANDLERS
# ─────────────────────────────────────────────

analyzer = MinerviniAnalyzer()


def format_criteria(criteria: dict) -> str:
    c = criteria['criteria']
    lines = [
        f"{'✅' if c['C1_price_above_150_200'] else '❌'} Price > MA150 & MA200",
        f"{'✅' if c['C2_150_above_200']       else '❌'} MA150 > MA200",
        f"{'✅' if c['C3_200_trending_up']      else '❌'} MA200 Trending Up",
        f"{'✅' if c['C4_50_above_150_200']     else '❌'} MA50 > MA150 & MA200",
        f"{'✅' if c['C5_price_above_50']       else '❌'} Price > MA50",
        f"{'✅' if c['C6_25pct_above_52wk_low'] else '❌'} 25%+ Above 52W Low",
        f"{'✅' if c['C7_within_25pct_of_high'] else '❌'} Within 25% of 52W High",
    ]
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Stock Analyze Karo", callback_data='analyze_menu')],
        [InlineKeyboardButton("📊 Top Setups Scan", callback_data='scan_top')],
        [InlineKeyboardButton("📚 Strategy Explain Karo", callback_data='strategy_info')],
        [InlineKeyboardButton("⚠️ Risk Management", callback_data='risk_mgmt')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (
        "🇮🇳 *Mark Minervini Indian Stock Analyst Bot*\n\n"
        "Namaste! Main tumhara AI Stock Market Analyst hoon.\n\n"
        "📈 *Main kya karta hoon:*\n"
        "• Minervini ki SEPA strategy se stocks screen karta hoon\n"
        "• Stage 2 uptrend mein stocks dhundta hoon\n"
        "• VCP (Volatility Contraction) patterns identify karta hoon\n"
        "• Proper Entry, Stop Loss aur Target deta hoon\n"
        "• Relative Strength ranking (vs Nifty) calculate karta hoon\n\n"
        "⬇️ *Neeche se choose karo:*"
    )
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)


async def analyze_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze a specific stock - /analyze RELIANCE"""
    if not context.args:
        await update.message.reply_text(
            "📝 *Usage:* `/analyze RELIANCE`\n\nExample: `/analyze TCS`",
            parse_mode='Markdown'
        )
        return

    symbol_raw = context.args[0].upper().strip()
    symbol = f"{symbol_raw}.NS" if not symbol_raw.endswith('.NS') else symbol_raw

    msg = await update.message.reply_text(f"⏳ *{symbol_raw}* analyze ho raha hai... Thoda wait karo!")

    try:
        result = analyzer.full_analysis(symbol)

        if result is None:
            await msg.edit_text(f"❌ *{symbol_raw}* ka data nahi mila. Symbol check karo.")
            return

        t = result['trade']
        c = result['criteria']
        v = result['vcp']

        # Build message
        text = (
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *{result['symbol']}* — Analysis\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎯 *Signal:* {result['signal']}\n"
            f"💰 *Current Price:* ₹{t['current_price']}\n"
            f"⭐ *RS Rating:* {result['rs_rating']}/99 {'🔥' if result['rs_rating'] >= 80 else ''}\n"
            f"📈 *SEPA Score:* {c['score']}% ({c['passed']}/{c['total']} criteria)\n\n"
            f"━━ *MINERVINI CRITERIA* ━━\n"
            f"{format_criteria(c)}\n\n"
            f"━━ *VCP PATTERN* ━━\n"
            f"{'✅ VCP Form Ho Raha Hai!' if v['vcp_forming'] else '⚪ VCP Abhi Nahi Hai'}\n"
            f"📌 Pivot Level: ₹{v['pivot']}\n"
            f"📉 Volume Dry Up: {'✅ Haan' if v['vol_drying'] else '❌ Nahi'}\n"
            f"🎯 Tight Bars: {v['tight_bars']}\n\n"
            f"━━ *TRADE PLAN* ━━\n"
            f"🟢 Entry: ₹{t['entry']} (pivot breakout)\n"
            f"🔴 Stop Loss: ₹{t['stop']}\n"
            f"🎯 Target 1 (2:1): ₹{t['target1']}\n"
            f"🎯 Target 2 (3:1): ₹{t['target2']}\n"
            f"⚖️ Risk:Reward = 1:{t['risk_reward']}\n"
            f"📦 Suggested Qty: {t['suggested_qty']} shares\n"
            f"   *(10L portfolio, 1% risk per trade)*\n\n"
            f"📊 ATR (14): ₹{t['atr']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ _Ye sirf educational analysis hai._\n"
            f"_Trading apni responsibility par karo._"
        )

        # Generate chart
        chart = generate_chart(symbol, result['df'], t)

        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=chart,
            caption=text,
            parse_mode='Markdown'
        )
        await msg.delete()

    except Exception as e:
        logger.error(f"Analysis error: {e}")
        await msg.edit_text(f"❌ Error aaya: {str(e)[:100]}")


async def scan_top_setups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan top Minervini setups from watchlist"""
    query = update.callback_query
    if query:
        await query.answer()
        chat_id = query.message.chat_id
        send = lambda txt, **kw: context.bot.send_message(chat_id=chat_id, text=txt, **kw)
    else:
        chat_id = update.effective_chat.id
        send = lambda txt, **kw: update.message.reply_text(txt, **kw)

    status = await context.bot.send_message(
        chat_id=chat_id,
        text="🔍 *Top 50 stocks scan ho rahe hain...*\n_Minervini SEPA criteria apply ho raha hai..._\n⏳ 2-3 minutes lagenge.",
        parse_mode='Markdown'
    )

    strong_buys = []
    watchlist_stocks = []

    for i, symbol in enumerate(WATCHLIST):
        try:
            result = analyzer.full_analysis(symbol)
            if result is None:
                continue

            if "STRONG BUY" in result['signal']:
                strong_buys.append(result)
            elif "WATCH" in result['signal']:
                watchlist_stocks.append(result)

            # Update progress every 10 stocks
            if (i + 1) % 10 == 0:
                await status.edit_text(
                    f"🔍 Scanning... {i+1}/{len(WATCHLIST)} stocks done",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Scan error for {symbol}: {e}")

    await status.delete()

    # Sort by RS rating
    strong_buys.sort(key=lambda x: x['rs_rating'], reverse=True)
    watchlist_stocks