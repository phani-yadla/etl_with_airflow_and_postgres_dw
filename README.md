# ETL_postgres_wh_with_airflow_on_docker
Deploying a ETL pipeline with airflow and finally loading the data to Postgres database using docker-compose.

In this project, we are aiming to first deploy a Postgres database using docker-compose along with airflow as a local deployment. 
Our next goal is to access sample data present in some public CSV files in a AWS S3 bucket, process them and store the processed data in our postgres database.
The pipeline is deployed as an airflow dag - "shopify_data_daily_dag", which pulls the data from the remote CSV files. After processing the data for each date ("extracted_date" field
in the data), the program connects with the postgres database and inserts the data in to it.

First let's start with local deployment and access the airflow UI to start the job.

## Installations and information

* Based on official [Airflow](https://github.com/apache/airflow/blob/main/docs/apache-airflow/start/docker-compose.yaml) image(apache/airflow:2.2.0) and uses the official [Postgres](https://hub.docker.com/_/postgres/) as backend and [Redis](https://hub.docker.com/_/redis/) as queue
* Install [Docker](https://www.docker.com/)
* Install [Docker Compose](https://docs.docker.com/compose/install/)
* Following the Airflow release from [Python Package Index](https://pypi.python.org/pypi/apache-airflow)

The Python libraries used are:
* Pandas: version 1.3.5 (within the Airflow image)
* Pytest: version 7.0.1
* Pathlib: version 1.0.1

## Initialize the database

On all operating systems, you need to run database migrations and create the first user account. To do it, run.

    docker compose -f airflow/docker-compose.yml up airflow-init

After initialization is completed, you can access the account created using login airflow and the password airflow.

## Running Airflow

Start all the services, including the postgres warehouse database as per the configurations made in the docker-composer.yml file:

    docker compose -f airflow/docker-compose.yml up


## Accessing the Airflow web interface and postgres database
 
Once the cluster has started up, you can log in to the web interface and try to run some tasks.

The airflow webserver is available at: http://localhost:8080. The default account has the login - "airflow" and the password - "airflow"

Please do these last steps on the UI to finalize the set up:
\
Step 1: Add a variable: 
 * Go to: Admin > Variables > + Add a new record 
 * Name the variable *shopify_pipeline_config* 
 * Assign it the following value
 ```
  {
    "url_pattern": "https://alg-data-public.s3.amazonaws.com/{}.csv",
    "start_date": "2019-04-01",
    "end_date": "2019-04-07",
    "db_table_name": "shopify_data"
  }
  ```

Step 2: Finally, add a connection to the PostgreSQL DB. \
Go to: Admin > Connections > + Add a new record \
Please add the following records in the corresponding cells:
* Connection Id -> postgres_default
* Connection Type -> Postgres 
* Host -> warehouse
* Login -> algolia
* Password -> algolia
* Port -> 5432

You're now ready to run the DAG.

 ### __RUNNING THE DATA PIPELINE__
 <a name="running-data-pipeline"></a>

#### __HOW TO CONFIGURE THE INPUT FILES TO BE FETCHED__
You can modify the requested data by updating the values of *start_date* and *end_date* in the variable *shopify_pipeline_config* variable. 

To query only one file and not a range of files (therefore for only one specific date), you can indicate the desired date in *start_date* and erase *end_date*.

You can also indicate the same date in *start_date* and *end_date* and the dag will as well only take into account the given date.

However: if you indicate only *end_date*, or neither *start_date* nor *start_date* then the dag will run taking into account today's date - 1 (yesterday), it means that only one file will be fetched, corresponding to the one ingested at 2 AM.

An assumption was made that the file generated at 2AM contains yesterday's date. 
To give an example, the file generated on 2022-02-26 at 2 AM, can be downloaded using the following url path: *alg-data-public.s3.amazonaws.com/2022-02-25.csv*

Once the dates are set, the DAG can be run.

#### __STRUCTURE OF THE DAG__

The first task creates a table called *shopify_data* in a dockerized PostgreSQL database.
The second task fetches the data (one or several csv files) from the given url, aggregates it (if more than one file), transfroms it and loads it into the *shopify_data* table.


### __TESTING__
<a name="testing"></a>
The functions used in the DAG were tested (tests can be found in *./tests/unit_tests*). 

The OSS Airflow project uses pytest, so the same was used in this project.

Before running the tests please install the required libs in your virtual environment by running the command:
```
$ pip install -r requirements.txt
```

Then copy the following command to run the unit tests:
```
$ PYTHONPATH=./airflow/dags pytest ./tests/unit_tests
```

### __Usage__

Once all the configurations are done, we can start the dag - "shopify_data_daily". Once the job is successfully completed, we can access the data from postgres database.

The postgres database could be accessed via any tool like pdadmin or DBeaver using the following credentials:
      - POSTGRES_USER=algolia
      - POSTGRES_PASSWORD=algolia
      - POSTGRES_DB=algolia
      - port = 5432
    (sometimes default port might be busy, check the port where postgres is available in your local if needed - "$ lsof -i -P" ) (try may be 5433 or 5438)

Also, in this example we are passing dates for which we need to processs as static parameters as per the scope of the aim. But we could pass date as a parameter, by running airflow dag with configs. When we deploy this pipeline as a daily job, we could use {{ ds }} to to execute the job dynamically everyday.
This way we could also use the same program for backfilling the data for the dates where it had issues.


## Cleaning up

To stop and delete containers,:

    docker compose -f airflow/docker-compose.yml down

To stop and delete containers, delete volumes with database data and download images, run:

    docker compose -f airflow/docker-compose.yml down --volumes --rmi all
