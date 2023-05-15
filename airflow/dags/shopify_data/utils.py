import logging
from typing import Iterator, List
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine
import psycopg2
from datetime import date, timedelta
from shopify_data.sql_queries import sql_insert_values


def generate_date_range(
    date1: datetime.date, date2: datetime.date
) -> Iterator[datetime.date]:
    """yields date1 + 1 day

    Args:
        date1 (datetime.date): the first date with date1 <= date2
        date2 (datetime.date): the second date with date2 >= date1

    Yields:
        Iterator[datetime.date]: yields date1 + 1 day
    """
    for n in range(int((date2 - date1).days) + 1):
        yield date1 + timedelta(n)
	
def fill_date_range(date1: datetime.date, date2: datetime.date) -> List[datetime.date]:
    """Takes two dates as input and gives a list of the date range
    between these two dates.

    Args:
        date1 (datetime.date) : the first date with date1 <= date2
        date2 (datetime.date) : the second date with date2 >= date1

    Returns:
        (list[datetime.date]) : list made out of the date range"""

    date_range_list = []

    if date1 == date2:
        date_range_list.append(date1.strftime("%Y-%m-%d"))
    else:
        for date in generate_date_range(date1, date2):
            date_range_list.append(date.strftime("%Y-%m-%d"))
    return date_range_list

def extract_data_to_df(
    url_formatted: str, start_date: datetime.date, end_date: datetime.date
) -> pd.DataFrame:
	"""Fetches remote csv files(from aws s3 bucket) within mentioned date ranges
	and merges them in to a single pandas dataframe.

    Args:
        url_formatted (str) : url to the remote file as a formatter string to add date
        start_date (datetime.date) : the second date with start_date <= end_date
        end_date (datetime.date) : the second date with date2 >= date1


    Returns:
        (pandas.DataFrame) : resulting pandas dataFrame from merging the data from the
		 					 remote csv files	
    """
    
	date_range_list = fill_date_range(start_date, end_date)
	input_dfs_list = []

	for date in date_range_list:
		url = url_formatted.format(date)
		try:
			input_df = pd.read_csv(url)
			input_dfs_list.append(input_df)
			logging.info(f"The following file was successfully loaded: {url}")
		except:
			logging.warn(f"The following file could not be loaded: {url}")
			pass

	input_full_df = pd.concat(input_dfs_list, ignore_index=True)

	return input_full_df	

def process_data(input_df: pd.DataFrame) -> pd.DataFrame:
	"""Process the fetched data according to business rules

    Args:
        input_df (pandas.DataFrame) : input data to be transformed

    Returns:
        (pandas.DataFrame) : transformed output
    """
	transformed_df = input_df[
		(input_df["application_id"].notnull()) & (input_df["application_id"] != "")
	]
	transformed_df["has_specific_prefix"] = np.where(
		transformed_df.loc[:, "index_prefix"] != "shopify_", True, False
	)

	return transformed_df

def load_data_to_postgres(conn, input_df: pd.DataFrame, table_name: str):
    """Loads rows in a sql database table given a pandas dataFrame.

    Args:
        conn (connection) : object connection to database
        df (pandas.DataFrame) : the dataFrame to insert in the database
        table_name (str) : the name of the table in which the data is loaded
    """
    tuples = [tuple(x) for x in input_df.to_numpy()]

    cols = ",".join(list(input_df.columns))
    query = sql_insert_values.format(table_name, cols)
    cursor = conn.cursor()
    try:
        psycopg2.extras.execute_values(cursor, query, tuples)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logging.error(f"Error: {error}")
        conn.rollback()
        cursor.close()
        return 1
    logging.info("The dataframe was successfully inserted")
    cursor.close()