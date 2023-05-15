from datetime import datetime, timedelta, date
from airflow import models
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.operators.postgres_operator import PostgresOperator
from airflow.hooks.postgres_hook import PostgresHook
from dateutil import parser
from shopify_data.sql_queries import sql_create_table
from shopify_data.utils import (
    extract_data_to_df,
    process_data,
    load_data_to_postgres,
)


config = models.Variable.get("shopify_pipeline_config", deserialize_json=True)
URL_PATTERN = config["url_pattern"]
TABLE_NAME = config["db_table_name"]

hook = PostgresHook()
conn = hook.get_conn()

if "start_date" in config.keys():
    start_date = parser.parse(config["start_date"]).date()

    if "end_date" in config.keys():
        end_date = parser.parse(config["end_date"]).date()

    else:
        end_date = start_date
else:
    yesterday = date.today() - timedelta(days=1)
    start_date = end_date = yesterday


def shopify_data_etl(
    url_pattern: str,
    start_date: datetime.date,
    end_date: datetime.date,
    table_name: str,
):
    """This function fetches one or several files (depending on the date range),
    creates a dataframe out of the aggregated data, transforms it given specific business rules,
    and then loads the output in a postgresql table.

    Args:
        url_pattern (str) : url missing the date part (that is added within the function)
        start_date (datetime.date) : the first date with start_date <= end_date
        end_date (datetime.date) : the second date with end_date >= start_date
        table_name (str) : the name of the table in which the data is loaded
    """
    input_data_df = extract_data_to_df(url_pattern, start_date, end_date)
    transformed_data_df = process_data(input_data_df)
    load_data_to_postgres(conn, transformed_data_df, table_name)


default_args = {
    "owner": "data_team",
    "retries": 0,
    "retry_delay": timedelta(minutes=1),
    # "on_failure_callback": failed_task_slack_notification,
}

with models.DAG(
    f"shopify_data_daily",
    default_args=default_args,
    schedule_interval="0 6 * * *",
    start_date=datetime(2023, 5, 14),
    tags=["daily_job", "shopify"],
    max_active_runs=1,  # for dags
    catchup=False,
) as dag:
    create_postgres_table = PostgresOperator(
        task_id="create_postgres_table",
        sql=sql_create_table,
    )

    etl_shopify_data = PythonOperator(
        task_id="process_and_load_data",
        python_callable=shopify_data_etl,
        op_kwargs={
            "url_pattern": URL_PATTERN,
            "start_date": start_date,
            "end_date": end_date,
            "table_name": TABLE_NAME,
        },
    )


create_postgres_table >> etl_shopify_data
