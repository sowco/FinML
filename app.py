import os
from fastapi import FastAPI
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

load_dotenv()

API_KEY = os.getenv("api_key_bybit")
API_SECRET = os.getenv("api_secret_bybit")

session = HTTP(testnet=True, api_key=API_KEY, api_secret=API_SECRET)

app = FastAPI(title="FinML Trading API")


@app.get("/")
def root():
    return {"message": "Trading API is running 🚀"}


@app.get("/balance")
def get_balance():
    """Получение баланса аккаунта"""
    try:
        result = session.get_wallet_balance(accountType="UNIFIED")
        balances = result.get("result", {}).get("list", [])
        return {"status": "ok", "balances": balances}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/positions/{coin}")
def get_positions(coin: str):
    """Получение позиций по конкретному инструменту"""
    try:
        result = session.get_positions(category="linear", symbol=coin)
        positions = result.get("result", {}).get("list", [])
        return {"status": "ok", "coin": coin, "positions": positions}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/status")
def get_status():
    """Общий статус торговли"""
    try:
        balance_data = session.get_wallet_balance(accountType="UNIFIED")
        balances = balance_data.get("result", {}).get("list", [])
        return {
            "status": "ok",
            "balances": balances,
            "server_time": session.server_time(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
