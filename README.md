# Lucid, in the Sky, with  Data.
A collection of scripts for manipulating and visualizing data from databases, dataframes, and cloud providers.

## Installation
Inside your repo: `git clone https://github.com/liquidcarbon/lucid.git`

## Usage
Add `lucid/*` to `.gitignore`.  If needed, amend `sys.path`:
```
import sys
sys.path.append('/path/to/lucid/')
import lucid
```

## Viz
[Bokeh](https://docs.bokeh.org/en/latest/index.html) is my favorite plotting library.
* `lucid.viz.TrueFalsePlot` for highlighting boolean relationships (see [example: is COVID incidence slowing or accelerating?](https://liquidcarbon.github.io/covid_weekly.html))
* `lucid.viz.CDF` for cumulative density function plots, with Kolmogorov–Smirnov / Kruskal–Wallis stats
```
import numpy as np
import pandas as pd
from bokeh.io import show

mu, sigma = 48, 20
data1 = pd.Series(np.random.normal(mu, sigma, 1000))
data2 = pd.Series(np.random.normal(52, 25,    2000))
cdf = lucid.viz.CDF('CDF distributions with optional KS metrics')
cdf.add_series(data1, 'rand normal 1', 'green')
cdf.add_series(data2, 'rand normal 2', 'red')
cdf.ks()
cdf.polish(xlabel='random')  # default range: 0 to 100
show(cdf.p)
```
![lucid CDF](https://user-images.githubusercontent.com/47034358/110200136-6a2d1e00-7e2a-11eb-885e-f20528f3b559.png)


## Databases
* wrappers for `pd.read_sql`:
    * tell you `df.shape` and SQL errors without 99 lines of traceback
    * adds query itself as a dataframe attribute: `df.q`, so you never forget which query produced which dataframe
* wrappers for common SQL queries:
    * `lucid.db.cd` for COUNT(DISTINCT ...)
    * `lucid.db.cgb` for COUNT(*) ... GROUP BY
    * `lucid.db.rcn` for RacCooN counts (rows, cardinality, nulls)
* table walk: data profiling tool that walks through every column of a table and returns cardinality, count of NULL values, and top N values as a dataframe
* schema walk: table walk across all tables in a schema


## Dataframes
A bunch of functions I found myself writing more than once, including:
* `lucid.df.ntop`: like table walk, but for a dataframe (rows, cardinality, nulls)
* `lucid.df.drop_empty_columns`: drop columns that are 100% NULL
* `lucid.df.gresample`: combine GROUP BY and resample for time series data


## IO
Writing [interactive jQuery web tables](https://liquidcarbon.github.io/covid_weekly.html) from pandas.  Writing multi-tab Excel files from pandas.  Working with streams.  


## Cloud Providers
Some AWS and GCP wrappers.



## Logging
I practice a flavor of [log-driven development](https://www.infoworld.com/article/3017687/get-started-with-log-driven-development.html).  Almost every function in `lucid` talks to you when it succeeds:

```
210306@02:16:09.180 DEBUG [lucid] lucid package (re)loaded
210306@02:16:09.913 INFO [lucid] [read_data]: read 3340 x 420 columns
210306@02:16:09.975 INFO [lucid] [agg_by_state]: aggregated to 56 x 54 columns
210306@02:16:09.982 INFO [lucid] [derivative] calculated derivative 1
210306@02:16:09.984 INFO [lucid] [derivative] calculated derivative 2
210306@02:16:10.487 INFO [lucid.io] [_make_j2html_basic] published page covid_weekly.html
```

...and when it fails:
```
210224@11:30:32.188 INFO [read_xpt_batch] loading dataset RXQ_RX_H ... 
210224@11:30:40.732 ERROR [read_xpt_batch] Something is wrong: 'utf-8' codec can't decode byte 0xf6 in position 18: invalid start byte
```

Boilerplate to enable logging to a file (`f`) or to a notebook (`h`) — pick one or both:
```
import logging
import sys

# I like this log format
formatter = logging.Formatter(
    fmt='%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s',
    datefmt='%y%m%d@%H:%M:%S',
)

lulogger = logging.getLogger('lucid')
lulogger.setLevel(logging.DEBUG)  # change to INFO or lower for fewer messages
f = logging.FileHandler('lucid.log')
f.setFormatter(formatter)
h = logging.StreamHandler(stream=sys.stdout)
h.setFormatter(formatter)

if not lulogger.hasHandlers():
    lulogger.addHandler(f)  # log to file
    lulogger.addHandler(h)  # log to STDOUT or Jupyter

import lucid
```

You should get:  `210306@02:16:09.180 DEBUG [lucid] lucid package (re)loaded`
