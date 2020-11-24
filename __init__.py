# lucid/__init__.py

__doc__ = """
Helpful scripts and libraries for working with databases, dataframes, and cloud providers
"""

import logging
import sys
logging.getLogger(__name__).addHandler(logging.NullHandler())

from . import aws
from . import db
from . import df
from . import io
from . import util
from . import viz

#-----------------------------------------------------------------------------
# Boilerplate for Notebooks
#   to use as a Jupyter template, add this code to snippets.json
#   and place in ~/.local/share/jupyter/nbextensions/snippets/
#   (requires Jupyter Notebook Extensions)
#-----------------------------------------------------------------------------

# import logging
# import sys


# # I like this log format
# formatter = logging.Formatter(
#     fmt='%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s',
#     datefmt='%y%m%d@%H:%M:%S',
# )

# lulogger = logging.getLogger('lucid')
# lulogger.setLevel(logging.DEBUG)  # change to INFO or lower for fewer messages
# # f = logging.FileHandler('lucid.log')
# # f.setFormatter(formatter)
# h = logging.StreamHandler(stream=sys.stdout)
# h.setFormatter(formatter)

# if not lulogger.hasHandlers():
#     lulogger.addHandler(f)  # log to file
#     lulogger.addHandler(h)  # log to STDOUT or Jupyter


# # Standard imports
# import os
# import pandas as pd
# import re


# # Options
# pd.options.display.max_rows = 96
# pd.options.display.max_columns = 96
# pd.options.display.max_colwidth = 128


# # Database connections
# conn = lucid.db.connect(**kwargs)


#-----------------------------------------------------------------------------
# A function to test logging
#-----------------------------------------------------------------------------

_l = logging.getLogger(__name__)
_l.debug(f'{__name__} package (re)loaded')
