from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount
from datetime import datetime, timedelta

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="bybit_monitoring",
    default_args=default_args,
    description="Run monitoring inside bybit_app container",
    schedule_interval="0 2 * * *",  
    start_date=datetime(2025, 10, 5),
    catchup=False,
    tags=["crypto", "monitoring"],
) as dag:

    monitoring_task = DockerOperator(
        task_id="run_monitoring",
        image="registry:5000/bybit_app:latest",
        docker_conn_id="docker_registry_conn",
        api_version="auto",
        auto_remove=True,
        command=["python", "/app/monitoring.py"],
        docker_url="tcp://docker-in-docker:2375",
        network_mode="bridge",
        mounts=[
            Mount(source="/home/sowco/dags/otus", target="/app", type="bind"),
            Mount(source="/home/sowco/.env", target="/app/.env", type="bind")
        ],
        do_xcom_push=True,
        tty=True
    )
