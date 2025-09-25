import os
import json
import pandas as pd
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
from backtesting import Backtest, Strategy
from utils import df_coin, add_features
import talib

# === Константы ===
RESULTS_FILE = "/app/best_results.json"
TP = 0.05
SL = 0.01
CASH = 30
COIN = "XRPUSDT"
INTERVAL = 60

# === Стратегия ===
class SignalStrategy(Strategy):
    sl = SL
    tp = TP

    def init(self):
        self.signal = self.data.Signal

    def next(self):
        signal = self.data.Signal[-1]
        current_price = self.data.Close[-1]

        if not self.position:
            if signal == 1:
                self.buy(
                    sl=current_price * (1 - self.sl),
                    tp=current_price * (1 + self.tp)
                )
            elif signal == -1:
                self.sell(
                    sl=current_price * (1 + self.sl),
                    tp=current_price * (1 - self.tp)
                )


# === Вспомогательные функции ===
def load_best_results():
    """Загрузить сохранённые лучшие результаты."""
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r") as f:
            return json.load(f)
    return {"best_params": None, "ann_return": -1e9}


def save_best_results(best_params, ann_return):
    """Сохранить лучшие результаты, если они лучше текущих."""
    best_results = load_best_results()
    if ann_return > best_results["ann_return"]:
        with open(RESULTS_FILE, "w") as f:
            json.dump(
                best_params,
                f,
                indent=4,
                ensure_ascii=False,
            )
        print("✅ Обновлены лучшие результаты!")
    else:
        print("⚠️ Результат хуже сохранённого, не обновляем.")


def get_data(session, feature_params, coin=COIN, period=360, interval=INTERVAL):
    """Загрузить данные по монете и добавить фичи."""
    df = df_coin(session, period=period, interval=interval, coin=coin)
    df = add_features(df, **feature_params)
    return df


def run_backtest(df):
    """Запустить бэктест стратегии и вернуть статистику и объект Backtest."""
    bt = Backtest(df, SignalStrategy, cash=CASH, commission=0.01)
    stats = bt.run()
    return stats, bt


def update_best_results(feature_params, stats):
    """Обновить лучшие результаты, если текущие лучше."""
    ann_return = stats["Return (Ann.) [%]"]

    # Объединяем feature_params и константы
    best_params = {
        "feature_params": feature_params,
        "constants": {
            "TP": TP,
            "SL": SL,
            "CASH": CASH,
            "COIN": COIN,
            "INTERVAL": INTERVAL
        },
        "ann_return": ann_return
    }
    save_best_results(best_params, ann_return)

# === Основная функция ===
def main():
    load_dotenv()

    API_KEY = os.getenv("api_key_bybit")
    API_SECRET = os.getenv("api_secret_bybit")

    session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)

    feature_params = dict(
        macd_fast=3,
        macd_slow=36,
        macd_signal=12,
        rsi_period=10,
        rsi_oversold=40,
        volume_window=5,
        volume_multiplier=1.2
    )

    # 1. Получаем данные
    df = get_data(session, feature_params)

    # 2. Запускаем бэктест
    stats, bt = run_backtest(df)

    print("=== Результаты бэктеста ===")
    print(stats[:27])

    # 3. Обновляем лучшие результаты
    update_best_results(feature_params, stats)

    # 4. Визуализация 
    try:
        bt.plot(filename="backtest_plot.html")
        print("График сохранён в backtest_plot.html")
    except Exception as e:
        print(f"Не удалось построить график: {e}")
    print(df.Signal.value_counts())


if __name__ == "__main__":
    main()
