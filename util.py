# lucid/util.py

__doc__ = """
Useful non-string functions.
"""


#-----------------------------------------------------------------------------
# Logging
#-----------------------------------------------------------------------------
import logging
_l = logging.getLogger(__name__)


#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
from datetime import datetime
from pandas import Timestamp
import inspect
import numpy as np
import pytz


#-----------------------------------------------------------------------------
# Utility Classes
#-----------------------------------------------------------------------------
class MattrD(dict):
    """ dictionary with keys accessible as class attributes """
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


#-----------------------------------------------------------------------------
# Utility Functions
#-----------------------------------------------------------------------------
def me(fmt='[{}]'):
    """ returns name of method for logging purposes """
    # _l.debug('this came from invoking `me` function in ./util.py')
    return fmt.format(inspect.stack()[1][3])


#-----------------------------------------------------------------------------
# File Functions
#-----------------------------------------------------------------------------


#-----------------------------------------------------------------------------
# Number Functions
#-----------------------------------------------------------------------------

def tryint(x, sub=-1):
    """Tries to convert object to integer.

    Like ``COALESCE(CAST(x as int), -1)`` but won't fail on `'1.23'`
    
    :Returns:
        int(x), ``sub`` value if fails (default: -1)
    """

    try:
        return int(x)
    except:
        return sub


#-----------------------------------------------------------------------------
# Date & Time
#-----------------------------------------------------------------------------
def tnow(z='America/Denver', fmt='%F_%H%M') -> str:
    """dated timestamp in a given timezone (defaults to MST)"""
    return datetime.now(tz=pytz.timezone(z)).strftime(fmt)

def week_number(d: Timestamp) -> int:
    """Returns the week number from a date."""
    try:
        return int(d.strftime('%V'))
    except AttributeError:
        return int(Timestamp(d).strftime('%V'))
    except Exception as e:
        _l.error(f'{me()} could not convert {d} to week number')
        return None
