import os
import time
import datetime
import requests
import pandas as pd
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
from backtesting import Backtest, Strategy
from datetime import datetime, timezone
from utils import df_coin, add_features, wait_for_candle, send_telegram_message

load_dotenv()

API_KEY = os.getenv("api_key_bybit")
API_SECRET = os.getenv("api_secret_bybit")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

session = HTTP(testnet=True, api_key=API_KEY, api_secret=API_SECRET)


def wait_for_candle(interval_min: int) -> float:
    now = datetime.now(timezone.utc)
    current_interval_start = now.replace(second=0, microsecond=0)
    seconds_past = (now - current_interval_start.replace(minute=(now.minute // interval_min) * interval_min)).total_seconds()
    sleep_secs = (interval_min * 60) - seconds_past
    if sleep_secs <= 0:
        sleep_secs += interval_min * 60
    return sleep_secs + 1


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("Сообщение отправлено в Telegram")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка отправки сообщения: {e}")


def place_new_order(session: HTTP, cfg: dict, coin: str, signal: int, price: float, qty: float) -> bool:
    side = 'Buy' if signal > 0 else 'Sell'
    tp_perc = cfg.get('tp', 0.1)
    sl_perc = cfg.get('sl', 0.015)
    leverage = float(cfg.get('leverage', 2))
    price_precision = cfg.get('price_precision', 5)
    try:
        if signal > 0:
            tp_price = price * (1 + tp_perc)
            sl_price = price * (1 - sl_perc)
        else:
            tp_price = price * (1 - tp_perc)
            sl_price = price * (1 + sl_perc)

        tp_price = round(tp_price, price_precision)
        sl_price = round(sl_price, price_precision)
        order_price = round(price, price_precision)
    except:
        ticker = session.get_tickers(category="linear", symbol=coin)
        if not ticker or 'result' not in ticker or 'list' not in ticker['result']:
            print("Не удалось получить цену тикера.")
            return False
        last_price = float(ticker['result']['list'][0]['lastPrice'])
        if signal > 0:
            tp_price = last_price * (1 + tp_perc)
            sl_price = last_price * (1 - sl_perc)
        else:
            tp_price = last_price * (1 - tp_perc)
            sl_price = last_price * (1 + sl_perc)
        tp_price = round(tp_price, price_precision)
        sl_price = round(sl_price, price_precision)
        order_price = round(last_price, price_precision)

    response = session.place_order(
        category="linear",
        symbol=coin,
        side=side,
        orderType='Market',
        qty=str(qty),
        price=None,
        takeProfit=tp_price,
        stopLoss=sl_price,
        timeInForce="GTC",
        positionIdx=1 if signal > 0 else 2,
        recv_window=10000
    )
    return response['retCode'] == 0 and 'orderId' in response['result']


if __name__ == "__main__":
    coin = "BTCUSDT"
    cfg = {"tp": 0.01, "sl": 0.005, "leverage": 2, "price_precision": 2}
    balance_start = 1000.0
    balance = balance_start

    while True:
        df = df_coin(period=2, interval=1, coin=coin)
        df = add_features(df)
        signal = df.iloc[-1]['Signal']
        price = df.iloc[-1]['prices_close']
        qty = 0.01

        if signal != 0:
            order_ok = place_new_order(session, cfg, coin, signal, price, qty)
            if order_ok:
                print(f"Ордер {signal} успешно выставлен по цене {price}")
            else:
                print("Ошибка при выставлении ордера")

        if balance < balance_start * 0.9:
            send_telegram_message("⚠️ Баланс снизился на 10%!")

        sleep_time = wait_for_candle(1)
        time.sleep(sleep_time)