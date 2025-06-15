# Copyright (c) 2018 gevent community
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
from __future__ import absolute_import, print_function, division

import sys
import functools
import unittest

from . import sysinfo
from . import six

class FlakyAssertionError(AssertionError):
    "Re-raised so that we know it's a known-flaky test."

# The next exceptions allow us to raise them in a highly
# greppable way so that we can debug them later.

class FlakyTest(unittest.SkipTest):
    """
    A unittest exception that causes the test to be skipped when raised.

    Use this carefully, it is a code smell and indicates an undebugged problem.
    """

class FlakyTestRaceCondition(FlakyTest):
    """
    Use this when the flaky test is definitely caused by a race condition.
    """

class FlakyTestTimeout(FlakyTest):
    """
    Use this when the flaky test is definitely caused by an
    unexpected timeout.
    """

class FlakyTestCrashes(FlakyTest):
    """
    Use this when the test sometimes crashes.
    """

def reraiseFlakyTestRaceCondition():
    six.reraise(FlakyAssertionError,
                FlakyAssertionError(sys.exc_info()[1]),
                sys.exc_info()[2])

reraiseFlakyTestTimeout = reraiseFlakyTestRaceCondition
reraiseFlakyTestRaceConditionLibuv = reraiseFlakyTestRaceCondition
reraiseFlakyTestTimeoutLibuv = reraiseFlakyTestRaceCondition

if sysinfo.RUNNING_ON_CI or (sysinfo.PYPY and sysinfo.WIN):
    # pylint: disable=function-redefined
    def reraiseFlakyTestRaceCondition():
        # Getting stack traces is incredibly expensive
        # in pypy on win, at least in test virtual machines.
        # It can take minutes. The traceback consistently looks like
        # the following when interrupted:

        # dump_stacks -> traceback.format_stack
        #    -> traceback.extract_stack -> linecache.checkcache
        #    -> os.stat -> _structseq.structseq_new

        # Moreover, without overriding __repr__ or __str__,
        # the msg doesn't get printed like we would want (its basically
        # unreadable, all printed on one line). So skip that.

        #msg = '\n'.join(dump_stacks())
        msg = str(sys.exc_info()[1])
        six.reraise(FlakyTestRaceCondition,
                    FlakyTestRaceCondition(msg),
                    sys.exc_info()[2])

    def reraiseFlakyTestTimeout():
        msg = str(sys.exc_info()[1])
        six.reraise(FlakyTestTimeout,
                    FlakyTestTimeout(msg),
                    sys.exc_info()[2])

    if sysinfo.LIBUV:
        reraiseFlakyTestRaceConditionLibuv = reraiseFlakyTestRaceCondition
        reraiseFlakyTestTimeoutLibuv = reraiseFlakyTestTimeout


def reraises_flaky_timeout(exc_kind=AssertionError, _func=reraiseFlakyTestTimeout):

    def wrapper(f):
        @functools.wraps(f)
        def m(*args):
            try:
                f(*args)
            except exc_kind:
                _func()
        return m

    return wrapper

def reraises_flaky_race_condition(exc_kind=AssertionError):
    return reraises_flaky_timeout(exc_kind, _func=reraiseFlakyTestRaceCondition)
