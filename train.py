import os
import datetime
import optuna
import pandas as pd
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
from backtesting import Backtest, Strategy
from utils import df_coin, add_features, wait_for_candle, send_telegram_message

load_dotenv()

API_KEY = os.getenv("api_key_bybit")
API_SECRET = os.getenv("api_secret_bybit")

session = HTTP(testnet=True, api_key=API_KEY, api_secret=API_SECRET)


class StrategyMA(Strategy):
    fast = 5
    slow = 20

    def init(self):
        close = self.data.Close
        self.ma_fast = self.I(lambda x: pd.Series(x).rolling(self.fast).mean(), close)
        self.ma_slow = self.I(lambda x: pd.Series(x).rolling(self.slow).mean(), close)

    def next(self):
        if self.ma_fast[-1] > self.ma_slow[-1] and not self.position:
            self.buy()
        elif self.ma_fast[-1] < self.ma_slow[-1] and self.position.is_long:
            self.position.close()
        elif self.ma_fast[-1] < self.ma_slow[-1] and not self.position:
            self.sell()
        elif self.ma_fast[-1] > self.ma_slow[-1] and self.position.is_short:
            self.position.close()


def objective(trial):
    fast = trial.suggest_int("fast", 3, 20)
    slow = trial.suggest_int("slow", 10, 50)

    if fast >= slow:
        return -1e9

    StrategyMA.fast = fast
    StrategyMA.slow = slow

    df = df_coin(period=30, interval=60, coin="BTCUSDT")
    bt = Backtest(df, StrategyMA, cash=10000, commission=0.001)
    stats = bt.run()

    return stats['Equity Final [$]']


if __name__ == "__main__":
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=50)

    print("Лучшие параметры:", study.best_params)
    print("Лучшая доходность:", study.best_value)
