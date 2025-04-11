# Copyright (c) 2009-2012 Denis Bilenko. See LICENSE for details.
"""
gevent is a coroutine-based Python networking library that uses greenlet
to provide a high-level synchronous API on top of libev event loop.

See http://www.gevent.org/ for the documentation.

.. versionchanged:: 1.3a2
   Add the `config` object.
"""

from __future__ import absolute_import

from collections import namedtuple

_version_info = namedtuple('version_info',
                           ('major', 'minor', 'micro', 'releaselevel', 'serial'))

#: The programatic version identifier. The fields have (roughly) the
#: same meaning as :data:`sys.version_info`
#: .. deprecated:: 1.2
#:  Use ``pkg_resources.parse_version(__version__)`` (or the equivalent
#:  ``packaging.version.Version(__version__)``).
version_info = _version_info(20, 0, 0, 'dev', 0) # XXX: Remove me

#: The human-readable PEP 440 version identifier.
#: Use ``pkg_resources.parse_version(__version__)`` or
#: ``packaging.version.Version(__version__)`` to get a machine-usable
#: value.
__version__ = '23.9.1'


__all__ = [
    'Greenlet',
    'GreenletExit',
    'Timeout',
    'config', # Added in 1.3a2
    'fork',
    'get_hub',
    'getcurrent',
    'getswitchinterval',
    'idle',
    'iwait',
    'joinall',
    'kill',
    'killall',
    'reinit',
    'setswitchinterval',
    'signal_handler',
    'sleep',
    'spawn',
    'spawn_later',
    'spawn_raw',
    'wait',
    'with_timeout',
]


import sys
if sys.platform == 'win32':
    # trigger WSAStartup call
    import socket  # pylint:disable=unused-import,useless-suppression
    del socket


# Floating point number, in number of seconds,
# like time.time
getswitchinterval = sys.getswitchinterval
setswitchinterval = sys.setswitchinterval

from gevent._config import config
from gevent._hub_local import get_hub
from gevent._hub_primitives import iwait_on_objects as iwait
from gevent._hub_primitives import wait_on_objects as wait

from gevent.greenlet import Greenlet, joinall, killall
spawn = Greenlet.spawn
spawn_later = Greenlet.spawn_later
#: The singleton configuration object for gevent.

from gevent.timeout import Timeout, with_timeout
from gevent.hub import getcurrent, GreenletExit, spawn_raw, sleep, idle, kill, reinit
try:
    from gevent.os import fork
except ImportError:
    __all__.remove('fork')

# This used to be available as gevent.signal; that broke in 1.1b4 but
# a temporary alias was added (See
# https://github.com/gevent/gevent/issues/648). It was ugly and complex and
# caused confusion, so it was removed in 1.5. See https://github.com/gevent/gevent/issues/1529
from gevent.hub import signal as signal_handler

# the following makes hidden imports visible to freezing tools like
# py2exe. see https://github.com/gevent/gevent/issues/181
# This is not well maintained or tested, though, so it likely becomes
# outdated on each major release.

def __dependencies_for_freezing(): # pragma: no cover
    # pylint:disable=unused-import, import-outside-toplevel
    from gevent import core
    from gevent import resolver_thread
    from gevent import resolver_ares
    from gevent import socket as _socket
    from gevent import threadpool
    from gevent import thread
    from gevent import threading
    from gevent import select
    from gevent import subprocess
    import pprint
    import traceback
    import signal as _signal

del __dependencies_for_freezing
