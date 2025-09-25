import os
import requests
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
from utils import send_telegram_message

load_dotenv()

API_KEY = os.getenv("api_key_bybit")
API_SECRET = os.getenv("api_secret_bybit")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)


def get_balance(coin="USDT"):
    try:
        resp = session.get_wallet_balance(accountType="UNIFIED")
        balances = resp["result"]["list"][0]["coin"]
        for b in balances:
            if b["coin"] == coin:
                return float(b["walletBalance"])
        return None
    except Exception as e:
        print(f"Ошибка получения баланса: {e}")
        return None


def run_monitoring():
    balance = get_balance("USDT")
    if balance is not None:
        message = f"💰 Баланс по счёту: {balance:.2f} USDT"
        send_telegram_message(message)
        print("Баланс успешно отправлен в Telegram")
    else:
        send_telegram_message("⚠️ Ошибка при получении баланса с Bybit")
        print("Не удалось получить баланс.")


if __name__ == "__main__":
    run_monitoring()