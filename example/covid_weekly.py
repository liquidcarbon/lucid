__doc__ = """
Sample script to showcase Lucid package.
"""


# add root folder to sys.path
import sys
sys.path.append(sys.path[0].rsplit('/', 2)[0])

# setup logging
import logging
_l = logging.getLogger('lucid')

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s',
    datefmt='%y%m%d@%H:%M:%S',
    stream=sys.stdout,
)
_l.setLevel(logging.DEBUG)

import lucid
import numpy as np
import os
import pandas as pd

from bokeh.embed import components
from lucid.util import me

# Pandas display options
pd.options.display.max_rows = 96
pd.options.display.max_columns = 96
pd.options.display.max_colwidth = 256

# Data Source: CSSE Daily US
# https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data/csse_covid_19_time_series
URL = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'

def read_data(datafile):
    """Read daily US COVID data."""

    df = pd.read_csv(datafile)
    _l.info('{0}: read {1[0]} x {1[1]} columns'.format(me(), df.shape))
    return df


def agg_by_state(df):
    """Calculates sum by state and weekly averages."""

    agg = df.groupby(
        ['Province_State']
    )[df.columns[list(df.columns).index('2/10/20'):]].sum().T
    agg.columns.name = ''
    agg.index = pd.DatetimeIndex(agg.index)
    agg = agg.resample('7D').mean().round(0).astype(int)
    agg = agg.loc[:, agg.iloc[len(agg)-1] > 1000]
    _l.info('{0}: aggregated to {1[0]} x {1[1]} columns'.format(me(), agg.shape))
    return agg


def derivative(df, n):
    """Returns n-th order derivative of numeric data."""

    d = df.copy()
    for i in range(n):
        d = (d - d.shift(1)).dropna()
        _l.info(f'{me()} calculated derivative {i+1}')
    return d


def prep_truefalse_plot(df):
    """Prepares data for TrueFalsePlot."""

    d1 = derivative(df, n=1)
    d2 = derivative(d1, n=1)
    tfp = pd.concat([
        (d2 > 0).stack(),
        d1.stack()
    ], axis=1).reset_index()
    tfp.columns = ['cols','rows','boolean','N']
    tfp['cols'] = tfp['cols'].apply(lambda x: x.strftime('%d-%b-%y'))
    return tfp.dropna()

df = agg_by_state(read_data(URL))
acceleration = prep_truefalse_plot(df)
tfp = lucid.viz.TrueFalsePlot(
    acceleration,
    plot_height=750,
    plot_width=800,
    title='True-False Plot: is COVID case count accelerating (red) or slowing (green)?',
    tooltips=[('','@cols @ @rows: +@N cases')],
    y_range=list(df.loc[max(df.index)].T.sort_values().index)
)

scr, div = components(tfp.p)
acceleration.columns = ['Date','State','Accelerating?','Average Daily Growth']
lucid.io.webtable(
    acceleration,
    'covid_weekly.html',
    content=div + '\n<hr>',
    title='COVID Weekly',
    scripts=scr,
    sort_col="1, 'asc'",
    footer=f'<br>Last Update: {lucid.util.tnow(fmt="%F %T")}',
    show_url=False,
)
