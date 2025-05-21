import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")



def get_timestamps():
    current_timestamp = int(time.time() * 1000)
    three_months_ago = datetime.now() - timedelta(days=3)  
    three_months_ago_timestamp = int(three_months_ago.timestamp() * 1000)
    return current_timestamp,three_months_ago_timestamp

def clean_data(ohlc_data):
    try:
        df = pd.DataFrame(ohlc_data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume',
                                            'quote_volume'])
    except:
        pass

    df['Close'] = df['Close'].astype(float)
    df['High'] = df['High'].astype(float)
    df['Open'] = df['Open'].astype(float)
    df['Low'] = df['Low'].astype(float)
    df['Volume'] = df['Volume'].astype(float)
    df['close'] = df['Close']
    df['high'] = df['High']
    df['low'] = df['Low']
    df['open'] = df['Open']
    df['volume'] = df['Volume']
    df['DateTime'] = pd.to_datetime(df['timestamp'],unit='ms')
    df.sort_values("timestamp", inplace=True)

    return df



def get_crypto_symbols(category="linear"):
    url = "https://api.bybit.com/v5/market/tickers"
    params = {
        "category": category  
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if "result" in data and "list" in data["result"]:
        df = pd.DataFrame(data["result"]["list"])
        return df["symbol"]
    else:
        raise ValueError("Unexpected response format")


def adaptive_supertrend(df, atr_len=10, factor=3, training_data_period=100, highvol=0.75, midvol=0.5, lowvol=0.25):
    hl2 = (df['High'] + df['Low']) / 2
    tr = np.maximum(df['High'] - df['Low'], 
                    np.maximum(abs(df['High'] - df['Close'].shift(1)), 
                               abs(df['Low'] - df['Close'].shift(1))))
    atr = tr.rolling(atr_len).mean()

    # Volatility Clustering with K-means-like centroid updates
    def cluster_volatility(vol_series):
        upper = vol_series.max()
        lower = vol_series.min()
        a = lower + (upper - lower) * highvol
        b = lower + (upper - lower) * midvol
        c = lower + (upper - lower) * lowvol

        for _ in range(10):  # limit to avoid infinite loops
            hv, mv, lv = [], [], []
            for v in vol_series:
                dists = [abs(v - a), abs(v - b), abs(v - c)]
                idx = np.argmin(dists)
                if idx == 0:
                    hv.append(v)
                elif idx == 1:
                    mv.append(v)
                else:
                    lv.append(v)
            new_a = np.mean(hv) if hv else a
            new_b = np.mean(mv) if mv else b
            new_c = np.mean(lv) if lv else c
            if new_a == a and new_b == b and new_c == c:
                break
            a, b, c = new_a, new_b, new_c
        return a, b, c

    df['ATR'] = atr
    hv, mv, lv = cluster_volatility(atr[-training_data_period:])
    
    # Assign cluster volatility to current ATR
    def assign_cluster_vol(v):
        dists = [abs(v - hv), abs(v - mv), abs(v - lv)]
        return [hv, mv, lv][np.argmin(dists)]

    adaptive_atr = atr.apply(assign_cluster_vol)

    # SuperTrend Calculation
    upperband = hl2 + factor * adaptive_atr
    lowerband = hl2 - factor * adaptive_atr

    supertrend = pd.Series(index=df.index, dtype='float64')
    direction = pd.Series(index=df.index, dtype='int')

    for i in range(len(df)):
        if i == 0:
            direction.iloc[i] = 1
            supertrend.iloc[i] = upperband.iloc[i]
        else:
            prev_st = supertrend.iloc[i - 1]
            prev_dir = direction.iloc[i - 1]

            lowerband.iloc[i] = max(lowerband.iloc[i], lowerband.iloc[i - 1]) if df['Close'].iloc[i - 1] >= lowerband.iloc[i - 1] else lowerband.iloc[i - 1]
            upperband.iloc[i] = min(upperband.iloc[i], upperband.iloc[i - 1]) if df['Close'].iloc[i - 1] <= upperband.iloc[i - 1] else upperband.iloc[i - 1]

            if prev_st == upperband.iloc[i - 1]:
                direction.iloc[i] = -1 if df['Close'].iloc[i] > upperband.iloc[i] else 1
            else:
                direction.iloc[i] = 1 if df['Close'].iloc[i] < lowerband.iloc[i] else -1

            supertrend.iloc[i] = lowerband.iloc[i] if direction.iloc[i] == -1 else upperband.iloc[i]

    df['SuperTrend'] = supertrend
    df['TrendDir'] = direction
    df['AdaptiveATR'] = adaptive_atr

    return df

def get_ohlc(symbol):
    url = "https://api.bybit.com/v5/market/kline"
    current_timestamp,three_months_ago_timestamp = get_timestamps()
    params = {
        "category":'linear',
        "symbol": symbol,
        "interval": "5",  
        "start": three_months_ago_timestamp,
        "end": current_timestamp    
    }

    response = requests.get(url, params=params)
    data = response.json()

    # Extracting and displaying the OHLC data
    if data["retCode"] == 0:
        df = clean_data(data["result"]['list'])
        return df

def check_signal(df,symbol):
    signal_cols = ['startLongTrade', 'startShortTrade', 'endLongTrade', 'endShortTrade']
    last_row = df.iloc[-1]
    for col in signal_cols:
        if pd.notna(last_row[col]):
            print(f"{symbol} Last signal: {col} at {last_row['DateTime']}")
            break

def check_signal_st_ml(df,symbol):
    if df['signal'].iloc[-1] == 'long':
        print(f"{symbol} Last signal: long at {df['DateTime'].iloc[-1]}")
    elif df['signal'].iloc[-1] == 'short':
        print(f"{symbol} Last signal: short at {df['DateTime'].iloc[-1]}")

crypto_symbols = get_crypto_symbols("linear")

for i in range(len(crypto_symbols)):
    symbol = crypto_symbols.iloc[i]
    df = get_ohlc(symbol)
    df = adaptive_supertrend(df)
    df['shifted_dir'] = df['TrendDir'].shift(-1)
    df['shifted_signal'] = np.where(
    (df['TrendDir'] == 1) & (df['shifted_dir'] == -1), 'short',
    np.where(
        (df['TrendDir'] == -1) & (df['shifted_dir'] == 1), 'long',
        np.nan
    ))
    df['signal'] = df['shifted_signal'].shift(1)
    check_signal_st_ml(df,symbol)
    test_checkpoint = 1 
    print(symbol)
