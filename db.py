# lucid/db.py
__doc__ = """
Database connections and broadly useful SQL queries.
"""
#-----------------------------------------------------------------------------
# Logging
#-----------------------------------------------------------------------------

import logging
_l = logging.getLogger(__name__)

#-----------------------------------------------------------------------------
# Imports & Options
#-----------------------------------------------------------------------------

# External Imports
import numpy as np
import os
import pandas as pd

# Internal Imports
from .util import me

#-----------------------------------------------------------------------------
# Globals & Constants
#-----------------------------------------------------------------------------

sql_status_msg = '{0} SQL response: {1[0]} rows x {1[1]} cols'


#-----------------------------------------------------------------------------
# Generic SQL queries
#-----------------------------------------------------------------------------

def sq(q, conn):
    """Runs a simple SQL query."""

    try:
        df = pd.read_sql(q, conn)
        clean_column_names(df)
        _l.info(sql_status_msg.format(me(), df.shape))
        return df
    except Exception as e:
        _l.error('SQL Error: {}'.format(e))
        return

def runquery(query, **kwargs) -> bool:
    """Determines if formatted SQL query need to be run, printed, or both.

    Helps troubleshoot dynamically built queries.

    :Usage:
        inside functions with SQL queries, insert::

            if not runquery(**sql_params):
                return

    :Returns:
        * ``True`` will run the SQL query
        * ``False`` will print and not run the query
    """

    if not kwargs['run']:
        if kwargs['print']:
            print(query)
        else:
            _l.warning('%s nothing to do' % me())
        return False

    else:
        if kwargs['print']:
            print(query)
        return True


def info_schema(conn, db, **kwargs) -> pd.DataFrame:
    """Retrieves information schema for a database.

    :Args:
        :conn: a Connection object
        :db: database name
    :Returns:
        INFORMATION_SCHEMA as Pandas DataFrame
    """

    sql_params = {
        'cols': '*',
        'db': db,
        'print': False,
        'run': True,
        'where': '1=1',
    }
    sql_params.update(**kwargs)

    q = '''
    SELECT {cols} FROM {db}.INFORMATION_SCHEMA.tables WHERE {where}
    '''.format(**sql_params)

    if not runquery(q, **sql_params):
        return

    try:
        df = pd.read_sql(q, conn)
        clean_column_names(df)

        _l.info(sql_status_msg.format(me(), df.shape))
        return df
    except Exception as e:
        _l.error('SQL Error: {}'.format(e))
        return


def schema_walk(conn, db, schema) -> pd.DataFrame:
    """Row and column counts for every table in schema."""

    output_cols = {
        'table': str,
        'rows': int,
        'columns': int,
        'names': str,
    }
    df = pd.DataFrame(columns=output_cols.keys())
    try:
        tables = info_schema(
            conn,
            db,
            cols = 'table_name',
            where = f"table_schema = '{schema}'",
        )
        for table in tables['table_name']:
            t = f'{schema}.{table}'
            # _l.debug(f'checking table {t}...\r')
            n_rows = pd.read_sql(f'SELECT COUNT(1) FROM {t}', conn).iat[0,0]
            columns = pd.read_sql(f'SELECT * FROM {t} LIMIT 0', conn)
            clean_column_names(columns)
            n_cols = len(columns.columns)
            cols = ', '.join(columns.columns)[:256]+'...'
            table_info = [table, n_rows, n_cols, cols]
            df.loc[len(df)] = table_info
        return df.astype(output_cols, errors='ignore')
    except Exception as e:
        _l.error('SQL Error: {}'.format(e))
        return

#-----------------------------------------------------------------------------
# Data Cleaning
#-----------------------------------------------------------------------------

def clean_column_names(df: pd.DataFrame) -> None:
    """Fixes awkward column names returned by some database engines.

    Dataframe is modified in place."""

    if df.columns[0][:0] == b'':  # Redshift column names come as bytes
        df.columns = [c.decode() for c in df.columns]
    if '.' in df.columns[0]:  # Hive gives "table_name.col_name"
        df.columns = [c.split('.')[1] for c in df.columns]
    return
