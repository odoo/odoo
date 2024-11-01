"""
Internal helpers for FFI implementations.
"""
from __future__ import print_function, absolute_import

import os
import sys

def _dbg(*args, **kwargs):
    # pylint:disable=unused-argument
    pass

#_dbg = print

def _pid_dbg(*args, **kwargs):
    kwargs['file'] = sys.stderr
    print(os.getpid(), *args, **kwargs)

CRITICAL = 1
ERROR = 3
DEBUG = 5
TRACE = 9

GEVENT_DEBUG_LEVEL = vars()[os.getenv("GEVENT_DEBUG", 'CRITICAL').upper()]

if GEVENT_DEBUG_LEVEL >= TRACE:
    _dbg = _pid_dbg
