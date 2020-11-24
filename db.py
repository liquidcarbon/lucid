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

NULL_VALUES = [None, np.nan, 'NULL', 'none']
SQL_STATUS_MSG = '{0} SQL response: {1[0]} rows x {1[1]} cols'


#-----------------------------------------------------------------------------
# Generic SQL queries
#-----------------------------------------------------------------------------

def sq(q, conn, log=True):
    """Runs a simple SQL query."""

    try:
        df = pd.read_sql(q, conn)
        clean_column_names(df)
        if log:
            _l.info(SQL_STATUS_MSG.format(me(), df.shape))
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


def cgb(conn, table, cols, **kwargs) -> pd.DataFrame:
    """Returns COUNT(1)...GROUP BY on ``cols`` (one or more, in SQL syntax).

    """

    sql_params = {
        'cols': cols,
        'log': True,
        'table': table,
        'print': False,
        'run': True,
        'where': '1=1',
    }
    sql_params.update(**kwargs)

    q = '''
    SELECT
        {cols},
        COUNT(1) AS count
    FROM {table}
    WHERE {where}
    GROUP BY {cols}
    ORDER BY count DESC
    '''.format(**sql_params)
    df = sq(q, conn, log=sql_params['log'])
    return df


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

        _l.info(SQL_STATUS_MSG.format(me(), df.shape))
        return df
    except Exception as e:
        _l.error('SQL Error: {}'.format(e))
        return


def schema_walk(conn, db, schema) -> pd.DataFrame:
    """Returns row and column counts for every table in schema."""

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
            # _l.debug(f'checking table {t}...')
            n_rows = sq(f'SELECT COUNT(1) FROM {t}', conn, log=False).iat[0,0]
            columns = sq(f'SELECT * FROM {t} LIMIT 0', conn, log=False)
            n_cols = len(columns.columns)
            cols = ', '.join(columns.columns)[:256]+'...'
            table_info = [table, n_rows, n_cols, cols]
            df.loc[len(df)] = table_info
        return df.astype(output_cols, errors='ignore')
    except Exception as e:
        _l.error('SQL Error: {}'.format(e))
        return


def table_walk(conn, table, n=3, comb=[], excl=[], encr=[]) -> pd.DataFrame:
    """Returns COUNT(1)...GROUP BY, cardinality, and top ``n`` values
    for every column in a table.

    Optionally includes column combinations (in SQL syntax).
    Optionally excludes columns.
    Optionally encrypts values (e.g. PII/PHI).
    """

    output_cols = {
        'table': str,
        'column(s)': str,
        'cardinality': int,
    }
    df = pd.DataFrame(
        columns=list(output_cols.keys()) + [f'top{i+1}' for i in range(n)]
    )

    _l.info(f'processing table {table} ...')
    try:
        columns = list(
            sq(f'SELECT * FROM {table} LIMIT 0', conn, log=False)
        )
        cgb_columns = columns + comb
        for c in cgb_columns:
            _l.debug(f'checking column(s) {c}...')
            if c not in excl:  # excluding specific columns
                counts = cgb(conn, table, c, log=False)
                if counts is None:
                    continue
                card = len(counts)
                col_info = [table, c, card]
            else:
                df.loc[len(df)] = [table, c] + ['excluded']*(n+1)
                continue

            n_rows = counts['count'].sum()
            for i in range(n):
                try:
                    value = counts.iat[i, 0]
                    if c in encr:  # encrypting non-NULLs in specific columns
                        if value not in NULL_VALUES:
                            value = 'encrypted'
                    col_info.append((
                        value,
                        counts.iat[i,-1],
                        round(counts.iat[i,-1]/n_rows*100, 1)
                    ))
                except IndexError:
                    col_info.append(None)
            df.loc[len(df)] = col_info
        _l.info(f'completed table {table}')
        return df.astype(output_cols, errors='ignore')
    except Exception as e:
        _l.error('Error: {}'.format(e))
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
