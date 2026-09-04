# 3. Resilient Market Data Fetcher (Binance Futures + Yahoo Finance Fallback)
@st.cache_data(ttl=60)
def fetch_klines(symbol="BTCUSDT", interval="1h", limit=100):
    # ניסיון ראשון: Binance Futures API (בדרך כלל לא חסום ב-AWS)
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

    # גיבוי: Yahoo Finance במידה ובינאנס חסום בשרת
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
