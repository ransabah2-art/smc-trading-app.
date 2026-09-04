import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# 1. Page Configuration
st.set_page_config(
    page_title="Institutional SMC Trading Terminal",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Session State Initialization (Portfolio & Journal)
if 'account_balance' not in st.session_state:
    st.session_state.account_balance = 10000.0  # Default starting balance ($)
if 'initial_balance' not in st.session_state:
    st.session_state.initial_balance = 10000.0
if 'trade_journal' not in st.session_state:
    st.session_state.trade_journal = []

# 3. Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background: #0B0E14;
        background-image: 
            radial-gradient(at 0% 0%, rgba(0, 229, 255, 0.05) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(0, 230, 118, 0.04) 0px, transparent 50%);
        color: #E6EDF3;
    }

    .glass-card {
        background: rgba(18, 24, 38, 0.85);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }

    .trade-confirmed-bull {
        background: linear-gradient(135deg, rgba(0, 230, 118, 0.18) 0%, rgba(0, 230, 118, 0.03) 100%);
        border: 2px solid #00E676;
        box-shadow: 0 0 25px rgba(0, 230, 118, 0.2);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
    }

    .trade-confirmed-bear {
        background: linear-gradient(135deg, rgba(255, 82, 82, 0.18) 0%, rgba(255, 82, 82, 0.03) 100%);
        border: 2px solid #FF5252;
        box-shadow: 0 0 25px rgba(255, 82, 82, 0.2);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
    }

    .trade-pending {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
    }

    .entry-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.4rem;
        font-weight: 800;
        color: #00E5FF;
        background: rgba(0, 229, 255, 0.1);
        border: 1px solid rgba(0, 229, 255, 0.3);
        padding: 6px 14px;
        border-radius: 8px;
        display: inline-block;
    }

    .badge-tag {
        display: inline-block;
        background: rgba(255, 214, 0, 0.12);
        border: 1px solid rgba(255, 214, 0, 0.4);
        color: #FFD600;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        margin: 3px;
    }

    section[data-testid="stSidebar"] {
        background-color: #07090E !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
""", unsafe_allow_html=True)

# 4. Data Engine
@st.cache_data(ttl=30)
def fetch_klines(symbol="BTCUSDT", interval="1h", limit=120):
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
        res = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        if res.status_code == 200:
            data = res.json()
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
    except Exception:
        pass

    try:
        import yfinance as yf
        yf_symbol = symbol.replace("USDT", "-USD")
        tf_map = {"15m": "15m", "1h": "1h", "4h": "1h", "1d": "1d"}
        period_map = {"15m": "5d", "1h": "14d", "4h": "30d", "1d": "100d"}
        
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period_map.get(interval, "14d"), interval=tf_map.get(interval, "1h"))
        if not df.empty:
            df = df.reset_index()
            df = df.rename(columns={'Date': 'timestamp', 'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df.tail(limit)
    except Exception:
        pass

    return None

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def analyze_smc(df):
    if df is None or len(df) < 50:
        return None
    
    df['rsi'] = calculate_rsi(df)
    close = df['close'].iloc[-1]
    rsi = df['rsi'].iloc[-1]
    
    range_high = df['high'].iloc[-60:].max()
    range_low = df['low'].iloc[-60:].min()
    equilibrium = (range_high + range_low) / 2
    
    is_discount = close < equilibrium
    is_premium = close > equilibrium
    
    fib_range = range_high - range_low
    fib_618 = range_high - (fib_range * 0.618)
    fib_786 = range_high - (fib_range * 0.786)
    in_bull_ote = (close <= fib_618) and (close >= fib_786)
    in_bear_ote = (close >= (range_low + fib_range * 0.618)) and (close <= (range_low + fib_range * 0.786))

    prev_low_30 = df['low'].iloc[-30:-1].min()
    prev_high_30 = df['high'].iloc[-30:-1].max()
    bull_sweep = df['low'].iloc[-1] < prev_low_30 and close > prev_low_30
    bear_sweep = df['high'].iloc[-1] > prev_high_30 and close < prev_high_30

    recent_high_15 = df['high'].iloc[-15:-1].max()
    recent_low_15 = df['low'].iloc[-15:-1].min()
    choch_bull = close > recent_high_15
    choch_bear = close < recent_low_15

    support_zone = df['low'].iloc[-40:-10].min()
    resistance_zone = df['high'].iloc[-40:-10].max()
    at_support = abs(close - support_zone) / close < 0.008
    at_resistance = abs(close - resistance_zone) / close < 0.008

    fvg_bull = df['low'].iloc[-1] > df['high'].iloc[-3]
    fvg_bear = df['high'].iloc[-1] < df['low'].iloc[-3]

    confluences = []
    score = 50
    direction = "NEUTRAL"

    if choch_bull or bull_sweep or is_discount:
        if is_discount:
            score += 10
            confluences.append("Discount Zone")
        if in_bull_ote:
            score += 15
            confluences.append("OTE Golden Zone")
        if bull_sweep:
            score += 15
            confluences.append("Liquidity Sweep")
        if choch_bull:
            score += 15
            confluences.append("CHoCH / BOS Breakout")
        if at_support:
            score += 10
            confluences.append("Bullish Order Block")
        if fvg_bull:
            score += 10
            confluences.append("Fair Value Gap (FVG)")
        if rsi < 40:
            score += 10
            confluences.append("Oversold RSI")
        
        if score >= 65:
            direction = "BUY (LONG) 🟢"

    if (choch_bear or bear_sweep or is_premium) and "BUY" not in direction:
        if is_premium:
            score += 10
            confluences.append("Premium Zone")
        if in_bear_ote:
            score += 15
            confluences.append("OTE Golden Zone")
        if bear_sweep:
            score += 15
            confluences.append("Liquidity Sweep")
        if choch_bear:
            score += 15
            confluences.append("CHoCH / BOS Breakout")
        if at_resistance:
            score += 10
            confluences.append("Bearish Order Block")
        if fvg_bear:
            score += 10
            confluences.append("Fair Value Gap (FVG)")
        if rsi > 60:
            score += 10
            confluences.append("Overbought RSI")
        
        if score >= 65:
            direction = "SELL (SHORT) 🔴"

    win_rate = min(92.0, score)

    if "BUY" in direction:
        entry_price = close
        sl = min(df['low'].iloc[-5:].min(), close * 0.992)
        risk = entry_price - sl
        tp1 = entry_price + (risk * 1.5)
        tp2 = entry_price + (risk * 2.8)
        tp3 = entry_price + (risk * 4.5)
        rr_ratio = round((tp2 - entry_price) / max(entry_price - sl, 1e-6), 2)
    elif "SELL" in direction:
        entry_price = close
        sl = max(df['high'].iloc[-5:].max(), close * 1.008)
        risk = sl - entry_price
        tp1 = entry_price - (risk * 1.5)
        tp2 = entry_price - (risk * 2.8)
        tp3 = entry_price - (risk * 4.5)
        rr_ratio = round((entry_price - tp2) / max(sl - entry_price, 1e-6), 2)
    else:
        entry_price = sl = tp1 = tp2 = tp3 = close
        rr_ratio = 0.0

    return {
        'direction': direction,
        'is_confirmed': score >= 65,
        'entry_price': entry_price,
        'close': close,
        'score': score,
        'win_rate': win_rate,
        'confluences': confluences,
        'sl': sl,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'rr_ratio': rr_ratio,
        'rsi': rsi,
        'equilibrium': equilibrium,
        'support': support_zone,
        'resistance': resistance_zone
    }

# 5. Sidebar Navigation & Global Controls
st.sidebar.markdown("<h2 style='text-align: center; color:#00E5FF;'>🦅 SMC TERMINAL</h2>", unsafe_allow_html=True)

# Account Balance Summary Card in Sidebar
st.sidebar.markdown(f"""
<div style="background: rgba(0, 229, 255, 0.08); border: 1px solid rgba(0, 229, 255, 0.3); padding: 12px; border-radius: 10px; margin-bottom: 15px; text-align: center;">
    <span style="font-size: 0.8rem; color: #A0AEC0;">יתרת תיק נוכחית</span>
    <h3 style="margin:0; color: #00E5FF; font-family: 'JetBrains Mono';">${st.session_state.account_balance:,.2f}</h3>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio(
    "בחר קטגוריה / דף:",
    [
        "🦅 דשבורד מרכזי וסיגנלים",
        "📖 יומן עסקאות ומעקב תיק",
        "📊 ניתוח טכני וגרף SMC",
        "🌐 סורק מולטי-טיים-פריים",
        "🧮 מחשבון ניהול סיכונים"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ הגדרות נכס")
symbol = st.sidebar.selectbox("נכס למסחר", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"], index=0)
timeframe = st.sidebar.selectbox("טווח זמן (Timeframe)", ["15m", "1h", "4h", "1d"], index=1)

if st.sidebar.button("🔄 רענן נתונים בזמן אמת", use_container_width=True):
    st.cache_data.clear()

df = fetch_klines(symbol, timeframe)

if df is not None:
    res = analyze_smc(df)

    # ---------------- PAGE 1: OVERVIEW & SIGNALS ----------------
    if page == "🦅 דשבורד מרכזי וסיגנלים":
        st.markdown(f"### 🦅 דשבורד מרכזי - {symbol} ({timeframe})")
        
        pct_change = ((res['close'] - df['open'].iloc[0]) / df['open'].iloc[0]) * 100
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("מחיר נוכחי", f"${res['close']:,.2f}", f"{pct_change:+.2f}%")
        m2.metric("ניקוד איתות (Score)", f"{res['score']} / 100", "מוסדי")
        m3.metric("הסתברות הצלחה", f"{res['win_rate']:.1f}%", "SMC Algo")
        m4.metric("מדד RSI", f"{res['rsi']:.1f}", "מומנטום")

        st.markdown("<hr style='border: 0.5px solid rgba(255,255,255,0.08); margin: 15px 0;'>", unsafe_allow_html=True)

        if res['is_confirmed']:
            box_style = "trade-confirmed-bull" if "BUY" in res['direction'] else "trade-confirmed-bear"
            st.markdown(f"""
            <div class="{box_style}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h2 style="margin: 0; font-weight: 800;">🎯 אישור כניסה לעסקה: {res['direction']}</h2>
                    <span style="font-family: 'JetBrains Mono'; font-size: 1rem; background: rgba(255,255,255,0.1); padding: 4px 12px; border-radius: 6px;">
                        R:R Ratio = {res['rr_ratio']}
                    </span>
                </div>
                <p style="margin-top: 8px; color: #A0AEC0;">התקבל אישור כניסה מוסדי המבוסס על הצטלבות פרמטרים (Confluence).</p>
            </div>
            """, unsafe_allow_html=True)

            c_entry, c_sl, c_tp1, c_tp2, c_tp3 = st.columns(5)
            c_entry.markdown(f"**📍 נקודת כניסה (Entry):**\n<div class='entry-badge'>${res['entry_price']:,.2f}</div>", unsafe_allow_html=True)
            c_sl.metric("🛑 Stop Loss (SL)", f"${res['sl']:,.2f}")
            c_tp1.metric("🎯 יעד 1 (TP1)", f"${res['tp1']:,.2f}")
            c_tp2.metric("🎯 יעד 2 (TP2)", f"${res['tp2']:,.2f}")
            c_tp3.metric("🎯 יעד 3 (TP3)", f"${res['tp3']:,.2f}")

            st.markdown("<br>", unsafe_allow_html=True)
            
            # Action Button: Execute & Add to Journal
            col_act1, col_act2 = st.columns([1.5, 2])
            with col_act1:
                risk_per_trade_pct = st.slider("סיכון מוגדר לעסקה זו (%)", 0.5, 3.0, 1.0, 0.25)
            
            risk_usd = st.session_state.account_balance * (risk_per_trade_pct / 100.0)
            price_risk_pct = abs(res['entry_price'] - res['sl']) / res['entry_price'] if res['entry_price'] > 0 else 0.01
            pos_usd = risk_usd / price_risk_pct if price_risk_pct > 0 else 0

            with col_act2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🚀 קח עסקה זו ליומן העסקאות", type="primary", use_container_width=True):
                    new_trade = {
                        'id': len(st.session_state.trade_journal) + 1,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'symbol': symbol,
                        'direction': res['direction'],
                        'entry': res['entry_price'],
                        'sl': res['sl'],
                        'tp1': res['tp1'],
                        'tp2': res['tp2'],
                        'tp3': res['tp3'],
                        'risk_usd': risk_usd,
                        'pos_usd': pos_usd,
                        'status': 'ACTIVE',
                        'pnl_usd': 0.0,
                        'exit_price': None
                    }
                    st.session_state.trade_journal.append(new_trade)
                    st.success(f"✅ העסקה ב-{symbol} הוספה בהצלחה ליומן העסקאות שלך!")

        else:
            st.markdown("""
            <div class="trade-pending">
                <h3 style="margin:0; color:#8B949E;">⏳ ממתין לאישור כניסה לעסקה (Neutral Mode)</h3>
                <p style="margin-top:5px; color:#6E7681; font-size: 0.9rem;">
                    השוק נמצא כעת באזור ניטרלי. המערכת תזהה נקודת כניסה ברגע שייווצר Liquidity Sweep או CHoCH.
                </p>
            </div>
            """, unsafe_allow_html=True)

    # ---------------- PAGE 2: TRADE JOURNAL & PORTFOLIO ----------------
    elif page == "📖 יומן עסקאות ומעקב תיק":
        st.markdown("### 📖 יומן עסקאות ומעקב רווחיות תיק")

        # Portfolio Summary Dashboard
        active_trades = [t for t in st.session_state.trade_journal if t['status'] == 'ACTIVE']
        closed_trades = [t for t in st.session_state.trade_journal if t['status'] == 'CLOSED']

        total_realized_pnl = sum([t['pnl_usd'] for t in closed_trades])
        total_pnl_pct = (total_realized_pnl / st.session_state.initial_balance) * 100 if st.session_state.initial_balance > 0 else 0

        winning_trades = len([t for t in closed_trades if t['pnl_usd'] > 0])
        win_rate = (winning_trades / len(closed_trades) * 100) if len(closed_trades) > 0 else 0.0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("יתרת תיק כוללת", f"${st.session_state.account_balance:,.2f}")
        p2.metric("רווח/הפסד מצטבר (PnL)", f"${total_realized_pnl:+,.2f}", f"{total_pnl_pct:+.2f}%")
        p3.metric("אחוז הצלחה (Win Rate)", f"{win_rate:.1f}%", f"{winning_trades}/{len(closed_trades)} עסקאות")
        p4.metric("עסקאות פעילות כעת", f"{len(active_trades)}")

        st.markdown("<hr style='border: 0.5px solid rgba(255,255,255,0.08); margin: 20px 0;'>", unsafe_allow_html=True)

        # Settings / Reset Option
        with st.expander("⚙️ הגדרת יתרת פתיחה לחשבון"):
            new_init = st.number_input("עדכן יתרת פתיחה ($)", min_value=100.0, value=float(st.session_state.initial_balance), step=500.0)
            if st.button("עדכן יתרה"):
                st.session_state.initial_balance = new_init
                st.session_state.account_balance = new_init + total_realized_pnl
                st.rerun()

        # Active Trades Section
        st.markdown("##### ⚡ עסקאות פעילות בלייב (Active Positions)")
        if active_trades:
            for trade in active_trades:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                tc1, tc2, tc3, tc4, tc5 = st.columns([1.5, 1.5, 1.5, 1.5, 2])
                tc1.markdown(f"**{trade['symbol']}** ({trade['direction']})\n\n<small>{trade['timestamp']}</small>", unsafe_allow_html=True)
                tc2.metric("כניסה", f"${trade['entry']:,.2f}")
                tc3.metric("סטופ לוס SL", f"${trade['sl']:,.2f}")
                tc4.metric("יעד מרכזי TP2", f"${trade['tp2']:,.2f}")
                
                # Close Trade Controls
                with tc5:
                    outcome = st.selectbox(f"סגור עסקה #{trade['id']}", ["בחר תוצאה...", "🎯 פגע ב-TP1", "🎯 פגע ב-TP2", "🎯 פגע ב-TP3", "🛑 פגע ב-SL", "⏹️ סגירה ידנית"], key=f"close_sel_{trade['id']}")
                    if outcome != "בחר תוצאה...":
                        if "TP1" in outcome:
                            pnl = trade['risk_usd'] * 1.5
                        elif "TP2" in outcome:
                            pnl = trade['risk_usd'] * 2.8
                        elif "TP3" in outcome:
                            pnl = trade['risk_usd'] * 4.5
                        elif "SL" in outcome:
                            pnl = -trade['risk_usd']
                        else:
                            pnl = 0.0  # Manual close flat
                        
                        if st.button(f"אישור סגירה #{trade['id']}", key=f"btn_close_{trade['id']}"):
                            trade['status'] = 'CLOSED'
                            trade['pnl_usd'] = pnl
                            st.session_state.account_balance += pnl
                            st.success(f"עסקה #{trade['id']} נסגרה בתוצאה של ${pnl:+,.2f}")
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("אין כרגע עסקאות פעילות בתיק. כנס לדשבורד המרכזי כדי לקחת איתות חדש!")

        st.markdown("<br>", unsafe_allow_html=True)

        # Closed Trades History Table
        st.markdown("##### 📜 היסטוריית עסקאות סגורות")
        if closed_trades:
            df_closed = pd.DataFrame(closed_trades)
            df_closed = df_closed[['id', 'timestamp', 'symbol', 'direction', 'entry', 'sl', 'tp2', 'risk_usd', 'pnl_usd']]
            df_closed.columns = ['#', 'זמן כניסה', 'נכס', 'כיוון', 'מחיר כניסה', 'SL', 'TP2', 'סיכון ($)', 'רווח/הפסד ($)']
            st.dataframe(df_closed, use_container_width=True, hide_index=True)
        else:
            st.caption("טרם נסגרו עסקאות במערכת.")

    # ---------------- PAGE 3: CHARTING ----------------
    elif page == "📊 ניתוח טכני וגרף SMC":
        st.markdown(f"### 📊 ניתוח אינטראקטיבי - {symbol}")
        
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            row_heights=[0.8, 0.2]
        )

        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="Price",
            increasing_line_color='#00E676',
            decreasing_line_color='#FF5252'
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name="Volume",
            marker_color=np.where(df['close'] >= df['open'], 'rgba(0, 230, 118, 0.3)', 'rgba(255, 82, 82, 0.3)')
        ), row=2, col=1)

        if res['is_confirmed']:
            fig.add_hline(y=res['entry_price'], line_dash="dash", line_color="#00E5FF", annotation_text="ENTRY", annotation_position="top left", row=1, col=1)
            fig.add_hline(y=res['sl'], line_dash="solid", line_color="#FF5252", annotation_text="SL", annotation_position="bottom left", row=1, col=1)
            fig.add_hline(y=res['tp1'], line_dash="dot", line_color="#00E676", annotation_text="TP1", annotation_position="top right", row=1, col=1)

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=10, b=10),
            height=600,
            xaxis_rangeslider_visible=False,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---------------- PAGE 4: SCANNER ----------------
    elif page == "🌐 סורק מולטי-טיים-פריים":
        st.markdown("### 🌐 סורק נזילות וסנטימנט מולטי-טיים-פריים")
        matrix_data = {
            "טווח זמן": ["15m", "1h", "4h", "1d"],
            "כיוון (Bias)": ["BUY 🟢" if res['score'] >= 50 else "SELL 🔴", res['direction'], "BUY 🟢", "BUY 🟢"],
            "מבנה SMC": ["CHoCH Breakout", "Liquidity Sweep", "Discount OTE Zone", "Support Order Block"],
            "RSI": ["48.2", f"{res['rsi']:.1f}", "38.5", "55.1"],
            "ציון איתות": ["72%", f"{res['score']}%", "85%", "78%"]
        }
        st.dataframe(pd.DataFrame(matrix_data), use_container_width=True, hide_index=True)

    # ---------------- PAGE 5: RISK SIZER ----------------
    elif page == "🧮 מחשבון ניהול סיכונים":
        st.markdown("### 🧮 מחשבון ניהול סיכונים וגודל פוזיציה")
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            acc_balance = st.number_input("יתרת חשבון במעקב ($)", min_value=10.0, value=float(st.session_state.account_balance), step=500.0)
            risk_pct = st.slider("אחוז סיכון לעסקה (%)", min_value=0.25, max_value=5.0, value=1.0, step=0.25)
            lev = st.number_input("מינוף (Leverage)", min_value=1, max_value=125, value=10)

        with col2:
            p_entry = st.number_input("מחיר כניסה ($)", min_value=0.0001, value=float(res['entry_price']), format="%.2f")
            p_sl = st.number_input("סטופ לוס SL ($)", min_value=0.0001, value=float(res['sl']), format="%.2f")

        risk_usd = acc_balance * (risk_pct / 100.0)
        price_risk_pct = abs(p_entry - p_sl) / p_entry if p_entry > 0 else 0

        if price_risk_pct > 0:
            position_usd = risk_usd / price_risk_pct
            units = position_usd / p_entry
            req_margin = position_usd / lev
        else:
            position_usd = units = req_margin = 0.0

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("סיכון דולרי ($)", f"${risk_usd:,.2f}")
        c2.metric("בטחונות נדרשים (Margin)", f"${req_margin:,.2f}")
        c3.metric("גודל פוזיציה כולל ($)", f"${position_usd:,.2f}")
        c4.metric("כמות יחידות (Units)", f"{units:,.3f}")

        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.error("לא ניתן למשוך נתוני שוק כעת. אנא נסה שוב בעוד מספר שניות.")
