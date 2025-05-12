from advanced_ta import LorentzianClassification
import requests
import pandas as pd
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



#####GET INDICATOR
def lorentzian_transormed_data( df: pd.DataFrame) -> pd.DataFrame:
    lc = LorentzianClassification(
        data = df,
        features=[
            LorentzianClassification.Feature("RSI", 14, 2),  # f1
            LorentzianClassification.Feature("WT", 10, 11),  # f2
            LorentzianClassification.Feature("CCI", 20, 2),  # f3
            LorentzianClassification.Feature("ADX", 20, 2),  # f4
            LorentzianClassification.Feature("RSI", 9, 2),   # f5
        ],
        settings=LorentzianClassification.Settings(
            source=df['Close'],
            neighborsCount=8,
            maxBarsBack=2000,
            useDynamicExits=False
        ),
        filterSettings=LorentzianClassification.FilterSettings(
            useVolatilityFilter=True,
            useRegimeFilter=True,
            useAdxFilter=False,
            regimeThreshold=-0.1,
            adxThreshold=20,
            kernelFilter = LorentzianClassification.KernelFilter(
                useKernelSmoothing = False,
                lookbackWindow = 8,
                relativeWeight = 8.0,
                regressionLevel = 25,
                crossoverLag = 2,
            )
        ))
    return lc.data



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



# def get_ohlc_new():
#     url = "https://api.bybit.com/v5/market/kline"
#     current_timestamp, start_timestamp = get_timestamps()

#     all_data = []
#     interval_minutes = 5
#     max_candles_per_request = 1000
#     interval_ms = interval_minutes * 60 * 1000
#     chunk_duration = interval_ms * max_candles_per_request

#     while start_timestamp < current_timestamp:
#         end_timestamp = min(start_timestamp + chunk_duration, current_timestamp)

#         params = {
#             "category": "linear",
#             "symbol": "BTCUSD",
#             "interval": "5",
#             "start": start_timestamp,
#             "end": end_timestamp
#         }

#         response = requests.get(url, params=params)
#         response.raise_for_status()
#         result = response.json()

#         if result.get("result") and result["result"].get("list"):
#             candles = result["result"]["list"]
#             all_data.extend(candles)

#             # Move start forward
#             last_timestamp = int(candles[-1][0])
#             start_timestamp = last_timestamp + interval_ms
#         else:
#             break

#         time.sleep(0.2)  # to avoid hitting rate limits

#     return all_data

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


crypto_symbols = get_crypto_symbols("linear")

for i in range(len(crypto_symbols)):
    symbol = crypto_symbols.iloc[i]
    df = get_ohlc(symbol)
    df  = lorentzian_transormed_data(df)
    last_signals = df[['startLongTrade', 'startShortTrade', 'endLongTrade', 'endShortTrade']].stack()
    check_signal(df,symbol)
    test_checkpoint = 1 
    # print(symbol)
