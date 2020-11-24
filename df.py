# lucid/df.py

__doc__ = """
Functions for exploring dataframes.
"""

#-----------------------------------------------------------------------------
# Logging
#-----------------------------------------------------------------------------
import logging
_l = logging.getLogger(__name__)


#-----------------------------------------------------------------------------
# Imports & Options
#-----------------------------------------------------------------------------

# External imports
from functools import reduce
import numpy as np
import pandas as pd
import re

# Lucid imports
from .util import me


#-----------------------------------------------------------------------------
# Globals & Constants
#-----------------------------------------------------------------------------


#-----------------------------------------------------------------------------
# Data Ingest
#-----------------------------------------------------------------------------
def read_selected_columns(file, exclude, **kwargs) -> pd.DataFrame():
    """Reads a CSV file with the exclusion of specified columns."""
    columns = pd.read_csv(file, nrows=0)
    usecols = [col for col in columns if col not in exclude]
    return pd.read_csv(file, usecols=usecols, **kwargs)


#-----------------------------------------------------------------------------
# Data Overview Functions
#-----------------------------------------------------------------------------
def mem(df, verbose=False):
    """Shows RAM footprint of a datafrane (df.info)."""
    return df.info(verbose=verbose, memory_usage='deep')


def vc(df, col, dropna=False):
    """Shortcut to Series.value_counts(dropna=False)."""
    return df[col].value_counts(dropna=dropna)


def topseries(series, n=7):
    """Shows top `n` values in Pandas series."""
    series_sorted = series.sort_values(ascending=False)
    topn = series_sorted.iloc[:n]
    topn = topn.append(
        pd.Series(series_sorted.iloc[n:].sum(), index=[' other'])
    )
    return topn


def top_items(df, col, n=1) -> list:
    """Returns cardinality and top `n` items from `col` in a `df`."""
    rel = 100 / len(df)
    counts = df[col].value_counts(dropna=False)
    c = len(counts)
    keys = counts.index[:n]
    vals = counts.values[:n]
    pcts = counts.values[:n] * rel
    return c, [[x, y, round(z, 1)] for x, y, z in zip(keys, vals, pcts)]


def ntop(df, n=3) -> pd.DataFrame:
    """Overview of top `n` items in all columns of a `df`."""
    df = df.loc[:, ~df.columns.duplicated()]
    dftop = pd.DataFrame(
        index=df.columns,
        columns=['cardinality','top_items','coverage'],
    )
    for col in df.columns:
        top = top_items(df, col, n=n)
        dftop.loc[col, 'cardinality'] = top[0]
        dftop.loc[col, 'coverage'] = sum([i[2] for i in top[1]])
        dftop.loc[col, 'top_items'] = top[1]
    return dftop


class Counts:
    """MapReduce implementation for COUNT ... GROUP BY on big data.
    
    Returns CGB and top ``n`` values from every column."""
    def __init__(self, file, ddl_file, n_cols=None, n_top=10):
        self.file = file
        self.columns = self._get_columns_from_ddl(ddl_file)
        self.conv = {
            'message__timestamp': ts_to_dt,
        }
        if n_cols:
            self.n = min(len(self.columns), n_cols)
        else:
            self.n = len(self.columns)
        # self.n_lines = sum(1 for l in gzip.open(file,'rb'))
        self.n_top = n_top
        self.result = {}
    
    @staticmethod
    def _get_columns_from_ddl(file):
        """Reads column headers from a DDL file derived from
        SHOW CREATE TABLE.
        """

        with open(file, 'r') as f:
            ddl = f.read()
        return ddl.split('`')[3::2]

    @staticmethod
    def _series_add(previous_result: pd.Series, new_result: pd.Series):
        """Reducing function for adding up the results across chunks.

        Equivalent to ``lambda a,b: a+b`` except takes advantage of
        ``fill_value`` in pd.Series.add"""
        return previous_result.add(new_result, fill_value=0)

    @staticmethod
    def _series_ntop(s: pd.Series, n: int, fillna='NULL'):
        """Returns top n values from a Pandas series."""
        vc = s.fillna(fillna).value_counts(dropna=False).head(n)
        return vc

    def count_chunks(self, sep='\t', chunksize=10000):
        self.chunks = pd.read_csv(
            self.file,
            sep=sep,
            chunksize=chunksize,
            header=None,
            low_memory=False,
            nrows=5e6,
            usecols=[i for i in range(self.n)],
        )

        # MAP
        counts = []
        for chunk in self.chunks:
            counts.append([self._series_ntop(chunk[c], None) for c in chunk.columns])
            _l.info('mapping chunk number {:>4}'.format(len(counts)))
        counts = np.array(counts)

        # REDUCE
        for i in range(self.n):
            print('reducing: {}'.format(self.columns[i]) + ' '*40, end='\r')
            self.result[self.columns[i]] = reduce(
                _series_add, counts[:,i]
            ).astype(int)

        # SORT by column names
        self.result = sorted(self.result.items())

    def summarize(self):
        """Summarize results in a neat dataframe."""

        #initialize result array
        result_columns = ['column','n_unique']
        for i in range(self.n_top):
            result_columns.append('top_%s\nvalue' % (i+1))
            result_columns.append('top_%s\ncount' % (i+1))
            result_columns.append('top_%s\nrel_count' % (i+1))
        result = [result_columns]

        #loop over result columns
        for col in self.result:
            # print('analyzing column: {}'.format(col[0]), end='\r')
            col_name = col[0].split('.')[-1]
            n_unique = len(col[1])
            col_summary = [col_name, n_unique]

            vc_abs = col[1].sort_values(ascending=False)
            vc_norm = (vc_abs / vc_abs.sum()).round(5) * 100

            for i in range(min(self.n_top, n_unique)):
                col_summary.append(vc_abs.index[i])
                col_summary.append(vc_abs.values[i])
                col_summary.append(vc_norm.values[i])
            result.append(col_summary)
        df = pd.DataFrame(columns=result[0], data=result[1:])
        df.insert(1, '100% NULL', 'FALSE')
        df.loc[
            (df['top_1\nvalue'] == 'NULL') & (df['n_unique'] == 1),
            '100% NULL'
        ] = 'TRUE'

        self.summary = df


#-----------------------------------------------------------------------------
# Data Quality Functions
#-----------------------------------------------------------------------------
def drop_empty_columns(df: pd.DataFrame, sort=True) -> pd.DataFrame:
    """Drops 100% NA columns."""
    empty = df.isna().all()
    _l.info(f'{me()} {sum(empty)} 100% NULL columns found')
    if sort:
        return df[sorted(df.columns[~empty])]
    else:
        return df[df.columns[~empty]]

def find_empty_columns(df: pd.DataFrame, sort=True) -> pd.DataFrame:
    """Finds 100% NA columns."""
    empty = df.isna().all()
    _l.info(f'{me()} {sum(empty)} 100% NULL columns found')
    return empty


#-----------------------------------------------------------------------------
# Pivots
#-----------------------------------------------------------------------------
def gresample(df, gb: list, dt: str, period: str, ag: dict):
    """Groupby, resample, and aggregate.
    
    :Args:
        :df: DataFrame
        :gb: list of GROUP BY columns
        :dt: datetime column
        :period: frequency ("7D","M","Q")
        :ag: dictionary of aggregation functions

    :Usage:
        safely combine groupby and resample::

            gresample(
                df,
                gb = ['State','City'],
                dt = 'Day',
                period = '7D',
                ag = {'EventID': lambda x: len(np.unique(x))}
            )
    """
    
    gresampled = df.groupby(gb + [pd.Grouper(freq=period, key=dt)]).agg(ag)
    return gresampled


#-----------------------------------------------------------------------------
# Data Typing
#-----------------------------------------------------------------------------
def detect_mixed_types(df):
    """ detects mixed dtypes that cause problem on loading to SQL """
    mixed = []
    for col in df.columns:
        type_counts = df[col].apply(type).value_counts(dropna=False)
        if len(type_counts) > 1:
            mixed.append(type_counts)
    return mixed
