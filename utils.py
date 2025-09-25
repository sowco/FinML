import datetime
import pandas as pd
import requests
from pybit.unified_trading import HTTP
import talib

def df_coin(session: HTTP, period: int, interval: int, coin: str) -> pd.DataFrame:
    import datetime
    import pandas as pd

    current_datetime = datetime.datetime.utcnow()
    end_date = current_datetime
    start_date = end_date - datetime.timedelta(days=period)

    result = session.get_kline(
        symbol=coin,
        interval=interval,
        start=int(start_date.timestamp() * 1000),
        end=int(end_date.timestamp() * 1000),
        limit=2000,
    )

    # Проверяем, есть ли данные
    if 'result' not in result or 'list' not in result['result'] or not result['result']['list']:
        raise ValueError(f"No candle data returned from API for {coin}. Result: {result}")

    df_list = result['result']['list']

    dates = [datetime.datetime.fromtimestamp(int(item[0]) / 1000.0) for item in df_list]
    prices_open = [float(item[1]) for item in df_list]
    prices_high = [float(item[2]) for item in df_list]
    prices_low = [float(item[3]) for item in df_list]
    prices_close = [float(item[4]) for item in df_list]
    volumes = [float(item[5]) for item in df_list]  

    df = pd.DataFrame({
        'Date': dates,
        'Open': prices_open,
        'High': prices_high,
        'Low': prices_low,
        'Close': prices_close,
        'Volume': volumes
    })

    df.set_index('Date', inplace=True)
    return df


def add_features(df, 
                 macd_fast=12, 
                 macd_slow=26, 
                 macd_signal=9, 
                 rsi_period=14,
                 rsi_oversold=35,
                 volume_window=20,
                 volume_multiplier=2.0):

    df = df.copy()
    df.columns = df.columns.str.capitalize()
    df = df[~df.index.duplicated(keep='last')]

    try: 
        df['RSI'] = talib.RSI(df['Close'], timeperiod=rsi_period)
    except:
        df['RSI'] = talib.RSI(df['Close'], timeperiod=7)

    try: 
        df['MACD'], df['MACD_signal'], _ = talib.MACD(
            df['Close'], fastperiod=macd_fast, slowperiod=macd_slow, signalperiod=macd_signal)
    except:
        df['MACD'], df['MACD_signal'], _ = talib.MACD(
            df['Close'], fastperiod=2, slowperiod=11, signalperiod=7)

    df['Volume_SMA'] = df['Volume'].rolling(window=volume_window).mean()
    df['Volume_Spike'] = df['Volume'] > df['Volume_SMA'] * volume_multiplier

    # Формируем сигналы
    buy_signal = (
        (df['RSI'] < rsi_oversold) &
        (df['MACD'] > df['MACD_signal']) &
        (df['Volume_Spike'])
    )

    sell_signal = (
        (df['RSI'] > 60) &
        (df['MACD'] < df['MACD_signal']) &
        (df['Volume_Spike'])
    )

    df['Signal'] = 0
    df.loc[buy_signal, 'Signal'] = 1
    df.loc[sell_signal, 'Signal'] = -1

    return df

def wait_for_candle(interval_min: int) -> float:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    current_interval_start = now.replace(second=0, microsecond=0)
    seconds_past = (now - current_interval_start.replace(minute=(now.minute // interval_min) * interval_min)).total_seconds()
    sleep_secs = (interval_min * 60) - seconds_past
    if sleep_secs <= 0:
        sleep_secs += interval_min * 60
    return sleep_secs + 1


def send_telegram_message(bot_token: str, chat_id: str, message: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("Сообщение отправлено в Telegram")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка отправки сообщения: {e}")
