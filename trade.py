import os
import sys
import time
from datetime import datetime, timezone
import requests
import json
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
from utils import df_coin, add_features, wait_for_candle, send_telegram_message

load_dotenv()

API_KEY = os.getenv("api_key_bybit")
API_SECRET = os.getenv("api_secret_bybit")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)

# === Загрузка сохраненных лучших результатов ===
RESULTS_FILE = "/app/best_results.json"
if os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE, "r") as f:
        best_results = json.load(f)
    constants = best_results.get("constants")
    if not constants:
        print("❌ Ошибка: файл best_results.json не содержит раздел 'constants'. Завершаем работу.")
        sys.exit(1)

    try:
        TP = constants["TP"]
        SL = constants["SL"]
        CASH = constants["CASH"]
        COIN = constants["COIN"]
        INTERVAL = constants["INTERVAL"]
    except KeyError as e:
        print(f"❌ Ошибка: отсутствует константа {e} в файле best_results.json. Завершаем работу.")
        sys.exit(1)
else:
    print(f"❌ Ошибка: файл {RESULTS_FILE} не найден. Завершаем работу.")
    sys.exit(1)

print(f"Используемые константы: TP={TP}, SL={SL}, CASH={CASH}, COIN={COIN}, INTERVAL={INTERVAL}")


def place_new_order(session: HTTP, cfg: dict, coin: str, signal: int, price: float, qty: float) -> bool:
    side = 'Buy' if signal > 0 else 'Sell'
    tp_perc = cfg.get('tp', TP)
    sl_perc = cfg.get('sl', SL)
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
    except Exception:
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


def run_trading_loop(coin=COIN, balance_start=CASH, cfg=None):
    if cfg is None:
        cfg = {"tp": TP, "sl": SL, "leverage": 2, "price_precision": 2}

    balance = balance_start

    while True:
        df = df_coin(session, period=2, interval=INTERVAL, coin=coin)
        df = add_features(df)
        signal = df.iloc[-1]['Signal']
        price = df.iloc[-1]['Close']
        qty = 0.01

        if signal != 0:
            order_ok = place_new_order(session, cfg, coin, signal, price, qty)
            if order_ok:
                print(f"Ордер {signal} успешно выставлен по цене {price}")
            else:
                print("Ошибка при выставлении ордера")

        if balance < balance_start * 0.9:
            send_telegram_message("⚠️ Баланс снизился на 10%!")

        sleep_time = wait_for_candle(INTERVAL)
        time.sleep(sleep_time)


if __name__ == "__main__":
    run_trading_loop()
