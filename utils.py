import datetime
import pandas as pd
import requests
from pybit.unified_trading import HTTP


def df_coin(session: HTTP, period: int, interval: int, coin: str) -> pd.DataFrame:
    current_datetime = datetime.datetime.utcnow()
    end_date = current_datetime
    max_period = period
    start_date = end_date - datetime.timedelta(days=max_period)
    result = session.get_index_price_kline(
        category="linear",
        symbol=coin,
        interval=interval,
        start=int(start_date.timestamp() * 1000),
        end=int(end_date.timestamp() * 1000),
        limit=1000,
    )
    dates = [datetime.datetime.fromtimestamp(int(item[0]) / 1000.0) for item in result['result']['list']]
    prices_open = [float(item[1]) for item in result['result']['list']]
    prices_max = [float(item[2]) for item in result['result']['list']]
    prices_min = [float(item[3]) for item in result['result']['list']]
    prices_close = [float(item[4]) for item in result['result']['list']]

    df = pd.DataFrame({
        'Date': dates,
        'Open': prices_open,
        'High': prices_max,
        'Low': prices_min,
        'Close': prices_close,
    })
    return df


def add_features(df: pd.DataFrame, fast: int = 5, slow: int = 20) -> pd.DataFrame:
    df['ma_fast'] = df['Close'].rolling(fast).mean()
    df['ma_slow'] = df['Close'].rolling(slow).mean()
    df['Signal'] = 0
    df.loc[df['ma_fast'] > df['ma_slow'], 'Signal'] = 1
    df.loc[df['ma_fast'] < df['ma_slow'], 'Signal'] = -1
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
