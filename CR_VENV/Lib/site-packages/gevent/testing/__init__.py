# Copyright (c) 2008-2009 AG Projects
# Copyright 2018 gevent community
# Author: Denis Bilenko
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import unittest

# pylint:disable=unused-import

# It's important to do this ASAP, because if we're monkey patched,
# then importing things like the standard library test.support can
# need to construct the hub (to check for IPv6 support using a socket).
# We can't do it in the testrunner, as the testrunner spawns new, unrelated
# processes.
from .hub import QuietHub
import gevent.hub
gevent.hub.set_default_hub_class(QuietHub)

try:
    import faulthandler
except ImportError:
    # The backport isn't installed.
    pass
else:
    # Enable faulthandler for stack traces. We have to do this here
    # for the same reasons as above.
    faulthandler.enable()

try:
    from gevent.libuv import _corecffi
except ImportError:
    pass
else:
    _corecffi.lib.gevent_test_setup() # pylint:disable=no-member
    del _corecffi

from .sysinfo import VERBOSE
from .sysinfo import WIN
from .sysinfo import LINUX
from .sysinfo import OSX
from .sysinfo import LIBUV
from .sysinfo import CFFI_BACKEND
from .sysinfo import DEBUG
from .sysinfo import RUN_LEAKCHECKS
from .sysinfo import RUN_COVERAGE

from .sysinfo import PY2
from .sysinfo import PY3
from .sysinfo import PY36
from .sysinfo import PY37
from .sysinfo import PY38
from .sysinfo import PY39
from .sysinfo import PY310

from .sysinfo import PYPY
from .sysinfo import PYPY3
from .sysinfo import CPYTHON

from .sysinfo import PLATFORM_SPECIFIC_SUFFIXES
from .sysinfo import NON_APPLICABLE_SUFFIXES
from .sysinfo import SHARED_OBJECT_EXTENSION

from .sysinfo import RUNNING_ON_TRAVIS
from .sysinfo import RUNNING_ON_APPVEYOR
from .sysinfo import RUNNING_ON_CI

from .sysinfo import RESOLVER_NOT_SYSTEM
from .sysinfo import RESOLVER_DNSPYTHON
from .sysinfo import RESOLVER_ARES
from .sysinfo import resolver_dnspython_available

from .sysinfo import EXPECT_POOR_TIMER_RESOLUTION

from .sysinfo import CONN_ABORTED_ERRORS

from .skipping import skipOnWindows
from .skipping import skipOnAppVeyor
from .skipping import skipOnCI
from .skipping import skipOnPyPy3OnCI
from .skipping import skipOnPyPy
from .skipping import skipOnPyPyOnCI
from .skipping import skipOnPyPyOnWindows
from .skipping import skipOnPyPy3
from .skipping import skipIf
from .skipping import skipUnless
from .skipping import skipOnLibev
from .skipping import skipOnLibuv
from .skipping import skipOnLibuvOnWin
from .skipping import skipOnLibuvOnCI
from .skipping import skipOnLibuvOnCIOnPyPy
from .skipping import skipOnLibuvOnPyPyOnWin
from .skipping import skipOnPurePython
from .skipping import skipWithCExtensions
from .skipping import skipOnLibuvOnTravisOnCPython27
from .skipping import skipOnPy37
from .skipping import skipOnPy310
from .skipping import skipOnPy3
from .skipping import skipWithoutResource
from .skipping import skipWithoutExternalNetwork
from .skipping import skipOnPy2
from .skipping import skipOnManylinux
from .skipping import skipOnMacOnCI

from .exception import ExpectedException


from .leakcheck import ignores_leakcheck


from .params import LARGE_TIMEOUT
from .params import DEFAULT_LOCAL_HOST_ADDR
from .params import DEFAULT_LOCAL_HOST_ADDR6
from .params import DEFAULT_BIND_ADDR
from .params import DEFAULT_BIND_ADDR_TUPLE
from .params import DEFAULT_CONNECT_HOST


from .params import DEFAULT_SOCKET_TIMEOUT
from .params import DEFAULT_XPC_SOCKET_TIMEOUT

main = unittest.main
SkipTest = unittest.SkipTest




from .sockets import bind_and_listen
from .sockets import tcp_listener

from .openfiles import get_number_open_files
from .openfiles import get_open_files

from .testcase import TestCase

from .modules import walk_modules

BaseTestCase = unittest.TestCase

from .flaky import reraiseFlakyTestTimeout
from .flaky import reraiseFlakyTestRaceCondition
from .flaky import reraises_flaky_timeout
from .flaky import reraises_flaky_race_condition

def gc_collect_if_needed():
    "Collect garbage if necessary for destructors to run"
    import gc
    if PYPY: # pragma: no cover
        gc.collect()

# Our usage of mock should be limited to '@mock.patch()'
# and other things that are easily...mocked...here on Python 2
# when mock is not installed.
try:
    from unittest import mock
except ImportError: # Python 2
    try:
        import mock
    except ImportError: # pragma: no cover
        # Backport not installed
        class mock(object):

            @staticmethod
            def patch(reason):
                return unittest.skip(reason)

mock = mock


# zope.interface
from zope.interface import verify
