# -*- coding: utf-8 -*-
"""
internal gevent python 2/python 3 bridges. Not for external use.
"""

from __future__ import print_function, absolute_import, division

## Important: This module should generally not have any other gevent
## imports (the exception is _util_py2)

import sys
import os


PY39 = sys.version_info[:2] >= (3, 9)
PY311 = sys.version_info[:2] >= (3, 11)
PY312 = sys.version_info[:2] >= (3, 11)
PYPY = hasattr(sys, 'pypy_version_info')
WIN = sys.platform.startswith("win")
LINUX = sys.platform.startswith('linux')
OSX = MAC = sys.platform == 'darwin'


PURE_PYTHON = PYPY or os.getenv('PURE_PYTHON')

## Types


string_types = (str,)
integer_types = (int,)
text_type = str
native_path_types = (str, bytes)
thread_mod_name = '_thread'

hostname_types = tuple(set(string_types + (bytearray, bytes)))

def NativeStrIO():
    import io
    return io.BytesIO() if str is bytes else io.StringIO()


from abc import ABC # pylint:disable=unused-import


## Exceptions

def reraise(t, value, tb=None): # pylint:disable=unused-argument
    if value.__traceback__ is not tb and tb is not None:
        raise value.with_traceback(tb)
    raise value
def exc_clear():
    pass



## import locks
try:
    # In Python 3.4 and newer in CPython and PyPy3,
    # imp.acquire_lock and imp.release_lock are delegated to
    # '_imp'. (Which is also used by importlib.) 'imp' itself is
    # deprecated. Avoid that warning.
    import _imp as imp
except ImportError:
    import imp # pylint:disable=deprecated-module
imp_acquire_lock = imp.acquire_lock
imp_release_lock = imp.release_lock

## Functions
iteritems = dict.items
itervalues = dict.values
xrange = range
izip = zip


## The __fspath__ protocol
from os import PathLike # pylint:disable=unused-import
from os import fspath
_fspath = fspath
from os import fsencode # pylint:disable=unused-import
from os import fsdecode # pylint:disable=unused-import

## Clocks
# Python 3.3+ (PEP 418)
from time import perf_counter
from time import get_clock_info
from time import monotonic
perf_counter = perf_counter
monotonic = monotonic
get_clock_info = get_clock_info


## Monitoring
def get_this_psutil_process():
    # Depends on psutil. Defer the import until needed, who knows what
    # it imports (psutil imports subprocess which on Python 3 imports
    # selectors. This can expose issues with monkey-patching.)
    # Returns a freshly queried object each time.
    try:
        from psutil import Process, AccessDenied
        # Make sure it works (why would we be denied access to our own process?)
        try:
            proc = Process()
            proc.memory_full_info()
        except AccessDenied: # pragma: no cover
            proc = None
    except ImportError:
        proc = None
    return proc
