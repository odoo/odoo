# Copyright (c) 2018 gevent. See LICENSE for details.
"""
The standard library :mod:`time` module, but :func:`sleep` is
gevent-aware.

.. versionadded:: 1.3a2
"""

from __future__ import absolute_import

__implements__ = [
    'sleep',
]

__all__ = __implements__

import time as __time__

from gevent._util import copy_globals

__imports__ = copy_globals(__time__, globals(),
                           names_to_ignore=__implements__)



from gevent.hub import sleep
sleep = sleep # pylint
