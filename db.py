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
    """Runs a simple SQL query.

    :Returns:
        pd.DataFrame with a new attr ``q`` to store the executed SQL query
    """

    try:
        df = pd.read_sql(q, conn)
        df.__setattr__('q', q)
        clean_column_names(df)
        if log:
            _l.info(SQL_STATUS_MSG.format(me(), df.shape))
        return df
    except Exception as e:
        if log is not None:
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


def cd(conn, table, cols, **kwargs):
    """Returns COUNT(DISTINCT) on ``cols`` (one or more, in SQL syntax).

    :Returns:
        * (count, distinct) if query succeeds
        * (-1, -1) if query fails
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
    WITH cd AS (
        SELECT
            {cols},
            COUNT(1) AS count
        FROM {table}
        WHERE {where}
        GROUP BY {cols}
    )
    SELECT
      SUM(count) as count,
      COUNT(*) as distinct
    FROM cd
    '''.format(**sql_params)
    df = sq(q, conn, log=sql_params['log'])
    if df is None:
        return -1, -1
    else:
        return df.fillna(0).iat[0,0], df.iat[0,1]


def cdn(conn, table, cols, where='1=1', **kwargs) -> pd.DataFrame:
    """Counts DISTINCT and NULL values in ``cols``.

    :Returns:
        pd.DataFrame
    """

    split = cols.split(',')

    all_where = f"{' IS NULL AND '.join(split)} IS NULL AND ({where})"
    all_null = cd(
        conn, table, cols,
        where=all_where,
        log=None,
    )

    any_where = f"{' IS NULL OR '.join(split)} IS NULL AND ({where})"
    any_null = cd(
        conn, table, cols,
        where=any_where,
        log=None,
    )

    df = pd.DataFrame(
        index=['count', 'distinct'],
        data={
            'all_null': all_null,
            'any_null': any_null,
    })
    return df


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
        'limit': 9_999_999,
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
    LIMIT {limit}
    '''.format(**sql_params)
    df = sq(q, conn, log=sql_params['log'])
    return df


def ct(conn, table, where='1=1', **kwargs) -> int:
    """Returns COUNT of rows with a ``where`` clause.

    :Returns:
        int
    """

    sql_params = {
        'log': True,
        'table': table,
        'print': False,
        'run': True,
        'where': where,
        'limit': 9_999_999,
    }
    sql_params.update(**kwargs)

    q = '''
    SELECT
        COUNT(*)
    FROM {table}
    WHERE {where}
    '''.format(**sql_params)

    df = sq(q, conn, log=sql_params['log'])
    try:
        return df.iat[0,0]
    except:
        return None


def rcn(conn, table, cols, **kwargs) -> pd.DataFrame:
    """Returns number of Rows, Cardinality, and number of NULLs in ``cols``.

    Optional ``where`` clauses accepted.
    NULL is included in unique values count.
    Mnemonic: RacCooN

    :Returns:
        * (rows, cardinality, nulls) if query succeeds
        * (-1, 0, 0) if query fails
    """

    r, c = cd(conn, table, cols, **kwargs)
    nulls = cdn(conn, table, cols, **kwargs)
    if nulls.loc['count','all_null'] == nulls.loc['count','any_null']:
        n = nulls.iat[0,0]
    else:
        c = (c, nulls.loc['distinct','any_null'])
        n = (nulls.loc['count','all_null'], nulls.loc['count','any_null'])
    return r, c, n


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


def table_walk(conn, table, x=3,
    comb=[], excl=[], encr=[], **kwargs) -> pd.DataFrame:
    """Returns an overview of the table.

    Includes COUNT...GROUP BY, cardinality, number of NULLs,
    and top ``x`` values for every column in a table.

    Optionally includes column combinations (in SQL syntax).
    Optionally excludes columns.
    Optionally encrypts values (e.g. PII/PHI).
    """

    output_cols = {
        'table': str,
        'column(s)': str,
        'cardinality': int,
        'nulls': int,
    }
    df = pd.DataFrame(
        columns=list(output_cols.keys()) + [f'top{i+1}' for i in range(x)]
    )

    _l.info(f'processing table {table} ...')

    try:
        columns = list(
            sq(f'SELECT * FROM {table} LIMIT 0', conn, log=False)
        )
        cgb_columns = columns + comb
        for col in cgb_columns:
            r, c, n = rcn(conn, table, col, log=None, **kwargs)
            col_info = [table, col, c, n]
            _l.debug(f'checking column(s) {col}: rcn = {r},{c},{n}')

            # if table is empty, stop the walk
            if r == 0:
                for col in cgb_columns:
                    df.loc[len(df)] = colinfo + [None] * x
                break

            # excluding big columns with high relative cardinality
            if type(c) == tuple:
                rc = c[0]/r
            else:
                rc = c/r
            if (c in excl) or ((rc > 0.9) and (r > 100_000)):
                df.loc[len(df)] = col_info + ['excluded']*x
                continue
            else:
                counts = cgb(conn, table, col, log=False, limit=100, **kwargs)
                if counts is None:
                    continue  # ignore entirely if COUNT...GROUP BY fails

            for i in range(x):
                try:
                    value = counts.iat[i, 0]

                    if col in encr:  # encrypting non-NULLs in specific columns
                        if value not in NULL_VALUES:
                            value = 'encrypted'
                    col_info.append((
                        value,
                        counts.iat[i,-1],
                        round(counts.iat[i,-1]/r*100, 1)
                    ))
                except IndexError:
                    col_info.append(None)
            df.loc[len(df)] = col_info

        _l.info(f'completed table {table}')
        return df.fillna('').astype(output_cols, errors='ignore')
    except Exception as e:
        _l.error('Error: {}'.format(e))
        raise(e)
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
