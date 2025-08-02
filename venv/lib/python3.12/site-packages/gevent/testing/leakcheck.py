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
from __future__ import print_function

import sys
import gc
from functools import wraps
import unittest

try:
    import objgraph
except ImportError: # pragma: no cover
    # Optional test dependency
    objgraph = None

import gevent
import gevent.core


def ignores_leakcheck(func):
    """
    Ignore the given object during leakchecks.

    Can be applied to a method, in which case the method will run, but
    will not be subject to leak checks.

    If applied to a class, the entire class will be skipped during leakchecks. This
    is intended to be used for classes that are very slow and cause problems such as
    test timeouts; typically it will be used for classes that are subclasses of a base
    class and specify variants of behaviour (such as pool sizes).
    """
    func.ignore_leakcheck = True
    return func

class _RefCountChecker(object):

    # Some builtin things that we ignore.
    # For awhile, we also ignored types.FrameType and types.TracebackType,
    # but those are important and often involved in leaks.
    IGNORED_TYPES = (tuple, dict,)
    try:
        CALLBACK_KIND = gevent.core.callback
    except AttributeError:
        # Must be using FFI.
        from gevent._ffi.callback import callback as CALLBACK_KIND


    def __init__(self, testcase, function):
        self.testcase = testcase
        self.function = function
        self.deltas = []
        self.peak_stats = {}

        # The very first time we are called, we have already been
        # self.setUp() by the test runner, so we don't need to do it again.
        self.needs_setUp = False

    def _ignore_object_p(self, obj):
        if obj is self:
            return False
        try:
            # Certain badly written __eq__ and __contains__ methods
            # (I'm looking at you, Python 3.10 importlib.metadata._text!
            # ``__eq__(self, other): return self.lower() == other.lower()``)
            # raise AttributeError which propagates here, and must be caught.
            # Similarly, we can get a TypeError
            if (
                obj in self.__dict__.values()
                or obj == self._ignore_object_p # pylint:disable=comparison-with-callable
            ):
                return False
        except (AttributeError, TypeError):
            # `obj` is things like that _text class. Also have seen
            # - psycopg2._psycopg.type
            # - relstorage.adapters.drivers._ClassDriverFactory
            return True

        kind = type(obj)
        if kind in self.IGNORED_TYPES:
            return False
        if kind is self.CALLBACK_KIND and obj.callback is None and obj.args is None:
            # these represent callbacks that have been stopped, but
            # the event loop hasn't cycled around to run them. The only
            # known cause of this is killing greenlets before they get a chance
            # to run for the first time.
            return False
        return True

    def _growth(self):
        return objgraph.growth(limit=None, peak_stats=self.peak_stats, filter=self._ignore_object_p)

    def _report_diff(self, growth):
        if not growth:
            return "<Unable to calculate growth>"

        lines = []
        width = max(len(name) for name, _, _ in growth)
        for name, count, delta in growth:
            lines.append('%-*s%9d %+9d' % (width, name, count, delta))

        diff = '\n'.join(lines)
        return diff


    def _run_test(self, args, kwargs):
        gc_enabled = gc.isenabled()
        gc.disable()

        if self.needs_setUp:
            self.testcase.setUp()
            self.testcase.skipTearDown = False
        try:
            self.function(self.testcase, *args, **kwargs)
        finally:
            self.testcase.tearDown()
            self.testcase.doCleanups()
            self.testcase.skipTearDown = True
            self.needs_setUp = True
            if gc_enabled:
                gc.enable()

    def _growth_after(self):
        # Grab post snapshot
        if 'urlparse' in sys.modules:
            sys.modules['urlparse'].clear_cache()
        if 'urllib.parse' in sys.modules:
            sys.modules['urllib.parse'].clear_cache() # pylint:disable=no-member

        return self._growth()

    def _check_deltas(self, growth):
        # Return false when we have decided there is no leak,
        # true if we should keep looping, raises an assertion
        # if we have decided there is a leak.

        deltas = self.deltas
        if not deltas:
            # We haven't run yet, no data, keep looping
            return True

        if gc.garbage:
            raise AssertionError("Generated uncollectable garbage %r" % (gc.garbage,))


        # the following configurations are classified as "no leak"
        # [0, 0]
        # [x, 0, 0]
        # [... a, b, c, d]  where a+b+c+d = 0
        #
        # the following configurations are classified as "leak"
        # [... z, z, z]  where z > 0

        if deltas[-2:] == [0, 0] and len(deltas) in (2, 3):
            return False

        if deltas[-3:] == [0, 0, 0]:
            return False

        if len(deltas) >= 4 and sum(deltas[-4:]) == 0:
            return False

        if len(deltas) >= 3 and deltas[-1] > 0 and deltas[-1] == deltas[-2] and deltas[-2] == deltas[-3]:
            diff = self._report_diff(growth)
            raise AssertionError('refcount increased by %r\n%s' % (deltas, diff))

        # OK, we don't know for sure yet. Let's search for more
        if sum(deltas[-3:]) <= 0 or sum(deltas[-4:]) <= 0 or deltas[-4:].count(0) >= 2:
            # this is suspicious, so give a few more runs
            limit = 11
        else:
            limit = 7
        if len(deltas) >= limit:
            raise AssertionError('refcount increased by %r\n%s'
                                 % (deltas,
                                    self._report_diff(growth)))

        # We couldn't decide yet, keep going
        return True

    def __call__(self, args, kwargs):
        for _ in range(3):
            gc.collect()

        # Capture state before; the incremental will be
        # updated by each call to _growth_after
        growth = self._growth()

        while self._check_deltas(growth):
            self._run_test(args, kwargs)

            growth = self._growth_after()

            self.deltas.append(sum((stat[2] for stat in growth)))


def wrap_refcount(method):

    if objgraph is None or getattr(method, 'ignore_leakcheck', False):
        if objgraph is None:
            import warnings
            warnings.warn("objgraph not available, leakchecks disabled")
        @wraps(method)
        def _method_skipped_during_leakcheck(self, *_args, **_kwargs):
            self.skipTest("This method ignored during leakchecks")
        return _method_skipped_during_leakcheck


    @wraps(method)
    def wrapper(self, *args, **kwargs): # pylint:disable=too-many-branches
        if getattr(self, 'ignore_leakcheck', False):
            raise unittest.SkipTest("This class ignored during leakchecks")
        return _RefCountChecker(self, method)(args, kwargs)

    return wrapper
