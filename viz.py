# lucid/viz.py

__doc__ = """
Useful Bokeh Plots.  Each Bokeh plot is exposed as ``self.p`` class attribute
and can be modified for final tweaks.
"""

#-----------------------------------------------------------------------------
# Logging
#-----------------------------------------------------------------------------
import logging
_l = logging.getLogger(__name__)


#-----------------------------------------------------------------------------
# Imports & Options
#-----------------------------------------------------------------------------

# Bokeh imports
from bokeh.colors import RGB
from bokeh.io import curdoc, output_file, show
from bokeh.models import ColorBar, LinearColorMapper
from bokeh.models import ColumnDataSource, HoverTool, Label, LabelSet
from bokeh.models import BasicTicker, FixedTicker
from bokeh.models import PrintfTickFormatter, NumeralTickFormatter
from bokeh.models import Range1d
from bokeh.plotting import figure
from bokeh.themes import Theme

# External imports
from math import pi
from pylab import cm
import numpy as np
import pandas as pd

# Lucid imports
from .util import me


#-----------------------------------------------------------------------------
# Globals & Constants
#-----------------------------------------------------------------------------

theme1 = {'attrs': {
    'Grid': {
        'grid_line_color': None,
    },

    'Title': {
        'text_font_size': '16pt',
        'text_font': 'Segoe UI'
    },

    'Axis': {
        'major_tick_in': -4,
        'major_tick_out': 8,
        'minor_tick_in': -2,
        'minor_tick_out': 4,
        'major_label_text_font_size': '14pt',
        'axis_label_text_font_size': '14pt',
        'axis_label_text_font': 'Segoe UI',
    },

    'Legend': {
        'background_fill_alpha': 0.4,
    }
}}
curdoc().theme = Theme(json=theme1)

# fill/hatch sequence for up to 20 categories
fill_hatch = {
    'fill': [
        '#ff0000',
        '#00ff00',
        '#0000ff',
        '#ffff00',
        '#00ffff',
        '#ff0000',
        '#00ff00',
        '#0000ff',
        '#ffff00',
        '#00ffff',
        '#ff0000',
        '#00ff00',
        '#0000ff',
        '#ffff00',
        '#00ffff',
        '#ff0000',
        '#00ff00',
        '#0000ff',
        '#ffff00',
        '#00ffff',
    ],
    'hatch': [
        ' ',
        ' ',
        ' ',
        ' ',
        ' ',
        ',',
        ',',
        ',',
        ',',
        ',',
        'v',
        'v',
        'v',
        'v',
        'v',
        'x',
        'x',
        'x',
        'x',
        'x',
    ]
}


#-----------------------------------------------------------------------------
# CDF Plot
#-----------------------------------------------------------------------------

class CDF:
    def __init__(self, title: str, **kwargs):
        self.p = figure(
            title=title,
            x_range=(0,102), y_range=(0,102),
            width=500, height=400,
            tools='', toolbar_location=None,
            background_fill_color="#ebebeb",
            **kwargs
        )

    def add_series(self, x: pd.Series, label, c, h=True):
        """Add a Pandas series."""
        N = len(x)
        if N > 10000:
            _x = x.sample(10000).sort_values()
        else:
            _x = x.sort_values()

        if h:
            hist, edges = np.histogram(_x, density=True, bins=20)
            self.p.quad(
                top=hist*500, bottom=0,
                left=edges[:-1], right=edges[1:],
                fill_color=c, line_color='white',
                line_width=2, alpha=0.5
            )

        y = np.linspace(0, 100, len(_x))
        self.p.line(
            _x, y,
            line_color=c, line_width=np.log10(N),
            alpha=0.75,
            legend_label=f"{label} (N={N})"
        )
        return

    def polish(self, xlabel, xrange=None, xticks=None):
        """Finishing touches on the plot."""
        if xrange:
            self.p.x_range=Range1d(xrange[0], xrange[1])
        self.p.legend.location = 'top_left'
        self.p.legend.background_fill_color = '#fefefe'
        self.p.xaxis.axis_label = xlabel
        self.p.yaxis.axis_label = '% of measurements'

        tickers = FixedTicker(
            ticks=[0, 25, 50, 75, 100],
            minor_ticks=[i*5 for i in range(1,20)]
        )
        if xticks:
            xtickers = FixedTicker(
                ticks=xticks[0],
                minor_ticks=xticks[1],
            )
        else:
            xtickers = tickers

        self.p.xaxis.ticker = xtickers
        self.p.yaxis.ticker = tickers
        self.p.grid.grid_line_color = "white"
        self.p.grid.grid_line_width = 2
        self.p.grid.minor_grid_line_color = 'gray'
        self.p.grid.minor_grid_line_alpha = 0.2
        return


#-----------------------------------------------------------------------------
# True-False Plot
#-----------------------------------------------------------------------------

class TrueFalsePlot:
    """A chart for highlighting boolean relationships.

    Requires a stacked dataset with at least three columns:
        ``['rows','cols','boolean']``
    """

    def __init__(self, df, plot=True,
                 colors=['seagreen', 'maroon'], **kwargs):

        mapper = LinearColorMapper(palette=colors, low=0, high=1)

        fig_args = {
            'title': 'True-False Plot',
            'plot_width': 960,
            'plot_height': 720,
            'tooltips': [('','@cols @ @rows')],
            'x_range': df.cols.unique(),
            'y_range': df.rows.unique(),
            'x_axis_location': 'above',
            'y_axis_location': 'right',
            'toolbar_location': None,
        }
        fig_args.update(**kwargs)

        p = figure(
            **fig_args,
        )

        p.grid.grid_line_color = None
        p.axis.axis_line_color = None
        p.axis.major_tick_line_color = None
        p.axis.major_label_standoff = 0
        p.xaxis.major_label_standoff = 0
        p.xaxis.major_label_text_font_size = '12px'
        p.yaxis.major_label_text_font_size = '12px'
        p.xaxis.major_label_orientation = 3.14 / 3

        p.rect(
            source=df,
            x='cols',
            y='rows',
            width=1, height=1,
            fill_color={'field': 'boolean', 'transform': mapper},
            fill_alpha=0.8,
            line_color='white', line_width=1,
        )

        self.p = p
        if plot:
            show(p)
        return
