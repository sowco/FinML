from airflow import DAG
from docker.types import Mount
from airflow.providers.docker.operators.docker import DockerOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="bybit_pipeline",
    default_args=default_args,
    description="Run backtest and trading inside bybit_app container",
    schedule_interval="0 0 * * 0",  # каждое воскресенье в 00:00 UTC
    start_date=datetime(2025, 9, 20),
    catchup=False,
    max_active_runs=1,
    tags=["crypto", "backtest", "trade"],
) as dag:
    # 0. Сначала закрываем прошлый цикл.
    close_positions = DockerOperator(
        task_id="close_positions",
        image="registry:5000/bybit_app:latest",
        docker_conn_id="docker_registry_conn",
        api_version="auto",
        auto_remove=True,
        command=["python", "/app/close_positions.py"], 
        docker_url="tcp://docker-in-docker:2375",
        network_mode="bridge",
        mounts=[
            Mount(source="/home/sowco/dags/otus", target="/app", type="bind"),
            Mount(source="/home/sowco/.env", target="/app/.env", type="bind")
        ],
        do_xcom_push=False,
        tty=True
    )

    # 1. Тренировка стратегии
    train_task = DockerOperator(
        task_id="train_strategy",
        image="registry:5000/bybit_app:latest",
        docker_conn_id="docker_registry_conn",
        api_version="auto",
        auto_remove=True,
        command=["python", "/app/train.py"],
        docker_url="tcp://docker-in-docker:2375",
        network_mode="bridge",
        mounts=[
            Mount(
                source="/home/sowco/dags/otus",
                target="/app",
                type="bind"
            ),
            Mount(
                source="/home/sowco/.env",
                target="/app/.env",
                type="bind"
            )
        ],
        do_xcom_push=True,
        tty=True
    )

    # 2. Торговля после тренировки
    trade_task = DockerOperator(
        task_id="run_trade",
        image="registry:5000/bybit_app:latest",
        docker_conn_id="docker_registry_conn",
        api_version="auto",
        auto_remove=True,
        command=["python", "/app/trade.py"],
        docker_url="tcp://docker-in-docker:2375",
        network_mode="bridge",
        mounts=[
            Mount(
                source="/home/sowco/dags/otus",
                target="/app",
                type="bind"
            ),
            Mount(
                source="/home/sowco/.env",
                target="/app/.env",
                type="bind"
            )
        ],
        do_xcom_push=True,
        tty=True
    )

    # Запуск по цепочке: сначала train, потом trade
    train_task >> trade_task
