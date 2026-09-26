# Copyright (c) 2009-2015 Denis Bilenko and gevent contributors. See LICENSE for details.
"""
Deprecated; this does not reflect all the possible options
and its interface varies.

.. versionchanged:: 1.3a2
    Deprecated.
"""
from __future__ import absolute_import

import sys

from gevent._config import config
from gevent._util import copy_globals

_core = sys.modules[config.loop.__module__]

copy_globals(_core, globals())

__all__ = _core.__all__ # pylint:disable=no-member
