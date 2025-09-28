import os
import sys
import json
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
from utils import send_telegram_message

RESULTS_FILE = "/app/best_results.json"

def load_coin_from_results():
    if not os.path.exists(RESULTS_FILE):
        msg = f"❌ Файл {RESULTS_FILE} не найден. Завершаем работу."
        raise FileNotFoundError(msg)

    with open(RESULTS_FILE, "r") as f:
        best_results = json.load(f)

    constants = best_results.get("constants")
    if not constants:
        raise ValueError("❌ Ошибка: файл best_results.json не содержит раздел 'constants'.")

    try:
        return constants["COIN"]
    except KeyError as e:
        raise KeyError(f"❌ Ошибка: отсутствует {e} в файле best_results.json.")

def main():
    load_dotenv()

    API_KEY = os.getenv("api_key_bybit")
    API_SECRET = os.getenv("api_secret_bybit")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    if not API_KEY or not API_SECRET:
        raise ValueError("API ключи Bybit не найдены в .env")

    coin = load_coin_from_results()
    symbol = f"{coin}" 

    print(f"▶ Работаем с монетой: {symbol}")

    session = HTTP(
        testnet=False,  
        api_key=API_KEY,
        api_secret=API_SECRET,
    )

    # 1. Отменяем открытые ордера
    try:
        print(f"Отменяю все открытые ордера по {symbol}...")
        session.cancel_all_orders(category="linear", symbol=symbol)
    except Exception as e:
        err_msg = f"⚠ Ошибка при отмене ордеров {symbol}: {e}"
        print(err_msg)
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, err_msg)

    # 2. Закрываем позицию
    try:
        print(f"Проверяю позиции по {symbol}...")
        positions = session.get_positions(category="linear", symbol=symbol)["result"]["list"]

        for pos in positions:
            if float(pos["size"]) > 0:
                side = "Sell" if pos["side"] == "Buy" else "Buy"
                qty = pos["size"]

                print(f"Закрываю {qty} {symbol}, направление: {pos['side']}")
                session.place_order(
                    category="linear",
                    symbol=symbol,
                    side=side,
                    orderType="Market",
                    qty=qty,
                    reduceOnly=True
                )
    except Exception as e:
        err_msg = f"⚠ Ошибка при закрытии позиции {symbol}: {e}"
        print(err_msg)
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, err_msg)

    print(f"✅ Все ордера и позиции по {symbol} закрыты.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        err_msg = f"❌ Критическая ошибка в close_positions.py: {e}"
        print(err_msg)

        load_dotenv()
        TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, err_msg)

        sys.exit(1)

