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
import os.path
from contextlib import contextmanager
from unittest import TestCase as BaseTestCase
from functools import wraps

import gevent
from gevent._util import LazyOnClass
from gevent._compat import perf_counter
from gevent._compat import get_clock_info
from gevent._hub_local import get_hub_if_exists

from . import sysinfo
from . import params
from . import leakcheck
from . import errorhandler
from . import flaky

from .patched_tests_setup import get_switch_expected

class TimeAssertMixin(object):
    @flaky.reraises_flaky_timeout()
    def assertTimeoutAlmostEqual(self, first, second, places=None, msg=None, delta=None):
        try:
            self.assertAlmostEqual(first, second, places=places, msg=msg, delta=delta)
        except AssertionError:
            flaky.reraiseFlakyTestTimeout()


    if sysinfo.EXPECT_POOR_TIMER_RESOLUTION:
        # pylint:disable=unused-argument
        def assertTimeWithinRange(self, time_taken, min_time, max_time):
            return
    else:
        def assertTimeWithinRange(self, time_taken, min_time, max_time):
            self.assertLessEqual(time_taken, max_time)
            self.assertGreaterEqual(time_taken, min_time)

    @contextmanager
    def runs_in_given_time(self, expected, fuzzy=None, min_time=None):
        if fuzzy is None:
            if sysinfo.EXPECT_POOR_TIMER_RESOLUTION or sysinfo.LIBUV:
                # The noted timer jitter issues on appveyor/pypy3
                fuzzy = expected * 5.0
            else:
                fuzzy = expected / 2.0
        min_time = min_time if min_time is not None else expected - fuzzy
        max_time = expected + fuzzy
        start = perf_counter()
        yield (min_time, max_time)
        elapsed = perf_counter() - start
        try:
            self.assertTrue(
                min_time <= elapsed <= max_time,
                'Expected: %r; elapsed: %r; min: %r; max: %r; fuzzy %r; clock_info: %s' % (
                    expected, elapsed, min_time, max_time, fuzzy, get_clock_info('perf_counter')
                ))
        except AssertionError:
            flaky.reraiseFlakyTestRaceCondition()

    def runs_in_no_time(
            self,
            fuzzy=(0.01 if not sysinfo.EXPECT_POOR_TIMER_RESOLUTION and not sysinfo.LIBUV else 1.0)):
        return self.runs_in_given_time(0.0, fuzzy)


class GreenletAssertMixin(object):
    """Assertions related to greenlets."""

    def assert_greenlet_ready(self, g):
        self.assertTrue(g.dead, g)
        self.assertTrue(g.ready(), g)
        self.assertFalse(g, g)

    def assert_greenlet_not_ready(self, g):
        self.assertFalse(g.dead, g)
        self.assertFalse(g.ready(), g)

    def assert_greenlet_spawned(self, g):
        self.assertTrue(g.started, g)
        self.assertFalse(g.dead, g)

    # No difference between spawned and switched-to once
    assert_greenlet_started = assert_greenlet_spawned

    def assert_greenlet_finished(self, g):
        self.assertFalse(g.started, g)
        self.assertTrue(g.dead, g)


class StringAssertMixin(object):
    """
    Assertions dealing with strings.
    """

    @LazyOnClass
    def HEX_NUM_RE(self):
        import re
        return re.compile('-?0x[0123456789abcdef]+L?', re.I)

    def normalize_addr(self, s, replace='X'):
        # https://github.com/PyCQA/pylint/issues/1127
        return self.HEX_NUM_RE.sub(replace, s) # pylint:disable=no-member

    def normalize_module(self, s, module=None, replace='module'):
        if module is None:
            module = type(self).__module__

        return s.replace(module, replace)

    def normalize(self, s):
        return self.normalize_module(self.normalize_addr(s))

    def assert_nstr_endswith(self, o, val):
        s = str(o)
        n = self.normalize(s)
        self.assertTrue(n.endswith(val), (s, n))

    def assert_nstr_startswith(self, o, val):
        s = str(o)
        n = self.normalize(s)
        self.assertTrue(n.startswith(val), (s, n))



class TestTimeout(gevent.Timeout):
    _expire_info = ''

    def __init__(self, timeout, method='Not Given'):
        gevent.Timeout.__init__(
            self,
            timeout,
            '%r: test timed out (set class __timeout__ to increase)\n' % (method,),
            ref=False
        )

    def _on_expiration(self, prev_greenlet, ex):
        from gevent.util import format_run_info
        loop = gevent.get_hub().loop
        debug_info = 'N/A'
        if hasattr(loop, 'debug'):
            debug_info = [str(s) for s in loop.debug()]
        run_info = format_run_info()
        self._expire_info = 'Loop Debug:\n%s\nRun Info:\n%s' % (
            '\n'.join(debug_info), '\n'.join(run_info)
        )
        gevent.Timeout._on_expiration(self, prev_greenlet, ex)

    def __str__(self):
        s = gevent.Timeout.__str__(self)
        s += self._expire_info
        return s

def _wrap_timeout(timeout, method):
    if timeout is None:
        return method

    @wraps(method)
    def timeout_wrapper(self, *args, **kwargs):
        with TestTimeout(timeout, method):
            return method(self, *args, **kwargs)

    return timeout_wrapper

def _get_class_attr(classDict, bases, attr, default=AttributeError):
    NONE = object()
    value = classDict.get(attr, NONE)
    if value is not NONE:
        return value
    for base in bases:
        value = getattr(base, attr, NONE)
        if value is not NONE:
            return value
    if default is AttributeError:
        raise AttributeError('Attribute %r not found\n%s\n%s\n' % (attr, classDict, bases))
    return default


class TestCaseMetaClass(type):
    # wrap each test method with
    # a) timeout check
    # b) fatal error check
    # c) restore the hub's error handler (see expect_one_error)
    # d) totalrefcount check
    def __new__(cls, classname, bases, classDict):
        # pylint and pep8 fight over what this should be called (mcs or cls).
        # pylint gets it right, but we cant scope disable pep8, so we go with
        # its convention.
        # pylint: disable=bad-mcs-classmethod-argument
        timeout = classDict.get('__timeout__', 'NONE')
        if timeout == 'NONE':
            timeout = getattr(bases[0], '__timeout__', None)
            if sysinfo.RUN_LEAKCHECKS and timeout is not None:
                timeout *= 6
        check_totalrefcount = _get_class_attr(classDict, bases, 'check_totalrefcount', True)

        error_fatal = _get_class_attr(classDict, bases, 'error_fatal', True)
        uses_handle_error = _get_class_attr(classDict, bases, 'uses_handle_error', True)
        # Python 3: must copy, we mutate the classDict. Interestingly enough,
        # it doesn't actually error out, but under 3.6 we wind up wrapping
        # and re-wrapping the same items over and over and over.
        for key, value in list(classDict.items()):
            if key.startswith('test') and callable(value):
                classDict.pop(key)
                # XXX: When did we stop doing this?
                #value = wrap_switch_count_check(value)
                value = _wrap_timeout(timeout, value)
                error_fatal = getattr(value, 'error_fatal', error_fatal)
                if error_fatal:
                    value = errorhandler.wrap_error_fatal(value)
                if uses_handle_error:
                    value = errorhandler.wrap_restore_handle_error(value)
                if check_totalrefcount and sysinfo.RUN_LEAKCHECKS:
                    value = leakcheck.wrap_refcount(value)
                classDict[key] = value
        return type.__new__(cls, classname, bases, classDict)

def _noop():
    return

class SubscriberCleanupMixin(object):

    def setUp(self):
        super(SubscriberCleanupMixin, self).setUp()
        from gevent import events
        self.__old_subscribers = events.subscribers[:]

    def addSubscriber(self, sub):
        from gevent import events
        events.subscribers.append(sub)

    def tearDown(self):
        from gevent import events
        events.subscribers[:] = self.__old_subscribers
        super(SubscriberCleanupMixin, self).tearDown()


class TestCase(TestCaseMetaClass("NewBase",
                                 (SubscriberCleanupMixin,
                                  TimeAssertMixin,
                                  GreenletAssertMixin,
                                  StringAssertMixin,
                                  BaseTestCase,),
                                 {})):
    __timeout__ = params.LOCAL_TIMEOUT if not sysinfo.RUNNING_ON_CI else params.CI_TIMEOUT

    switch_expected = 'default'
    #: Set this to true to cause errors that get reported to the hub to
    #: always get propagated to the main greenlet. This can be done at the
    #: class or method level.
    #: .. caution:: This can hide errors and make it look like exceptions
    #:    are propagated even if they're not.
    error_fatal = True
    uses_handle_error = True
    close_on_teardown = ()
    # This is really used by the SubscriberCleanupMixin
    __old_subscribers = () # pylint:disable=unused-private-member

    def run(self, *args, **kwargs): # pylint:disable=signature-differs
        if self.switch_expected == 'default':
            self.switch_expected = get_switch_expected(self.fullname)
        return super(TestCase, self).run(*args, **kwargs)

    def setUp(self):
        super(TestCase, self).setUp()
        # Especially if we're running in leakcheck mode, where
        # the same test gets executed repeatedly, we need to update the
        # current time. Tests don't always go through the full event loop,
        # so that doesn't always happen. test__pool.py:TestPoolYYY.test_async
        # tends to show timeouts that are too short if we don't.
        # XXX: Should some core part of the loop call this?
        hub = get_hub_if_exists()
        if hub and hub.loop:
            hub.loop.update_now()
        self.close_on_teardown = []
        self.addCleanup(self._tearDownCloseOnTearDown)

    def _callTestMethod(self, method):
        # 3.12 started raising a stupid warning about returning
        # non-None from ``test_...()`` being deprecated. Since the
        # test framework never cares about the return value anyway,
        # this is an utterly pointless annoyance. Override the method
        # that raises that deprecation. (Are the maintainers planning
        # to make the return value _mean_ something someday? That's
        # the only valid reason for them to do this. Answer: No, no
        # they're not. They're just trying to protect people from
        # writing broken tests that accidentally turn into generators
        # or something. Which...if people don't notice their tests
        # aren't working...well. Now, perhaps this got worse in the
        # era of asyncio where *everything* is a generator. But that's
        # not our problem; we have better ways of dealing with the
        # shortcomings of asyncio, namely, don't use it.
        # https://bugs.python.org/issue41322)
        method()

    def tearDown(self):
        if getattr(self, 'skipTearDown', False):
            del self.close_on_teardown[:]
            return

        cleanup = getattr(self, 'cleanup', _noop)
        cleanup()
        self._error = self._none
        super(TestCase, self).tearDown()

    def _tearDownCloseOnTearDown(self):
        while self.close_on_teardown:
            x = self.close_on_teardown.pop()
            close = getattr(x, 'close', x)
            try:
                close()
            except Exception: # pylint:disable=broad-except
                pass

    def _close_on_teardown(self, resource):
        """
        *resource* either has a ``close`` method, or is a
        callable.
        """
        self.close_on_teardown.append(resource)
        return resource

    @property
    def testname(self):
        return getattr(self, '_testMethodName', '') or getattr(self, '_TestCase__testMethodName')

    @property
    def testcasename(self):
        return self.__class__.__name__ + '.' + self.testname

    @property
    def modulename(self):
        return os.path.basename(sys.modules[self.__class__.__module__].__file__).rsplit('.', 1)[0]

    @property
    def fullname(self):
        return os.path.splitext(os.path.basename(self.modulename))[0] + '.' + self.testcasename

    _none = (None, None, None)
    # (context, kind, value)
    _error = _none

    def expect_one_error(self):
        self.assertEqual(self._error, self._none)
        gevent.get_hub().handle_error = self._store_error

    def _store_error(self, where, t, value, tb):
        del tb
        if self._error != self._none:
            gevent.get_hub().parent.throw(t, value)
        else:
            self._error = (where, t, value)

    def peek_error(self):
        return self._error

    def get_error(self):
        try:
            return self._error
        finally:
            self._error = self._none

    def assert_error(self, kind=None, value=None, error=None, where_type=None):
        if error is None:
            error = self.get_error()
        econtext, ekind, evalue = error
        if kind is not None:
            self.assertIsInstance(kind, type)
            self.assertIsNotNone(
                ekind,
                "Error must not be none %r" % (error,))
            assert issubclass(ekind, kind), error
        if value is not None:
            if isinstance(value, str):
                self.assertEqual(str(evalue), value)
            else:
                self.assertIs(evalue, value)
        if where_type is not None:
            self.assertIsInstance(econtext, where_type)
        return error

    def assertMonkeyPatchedFuncSignatures(self, mod_name, func_names=(), exclude=()):
        # If inspect.getfullargspec is not available,
        # We use inspect.getargspec because it's the only thing available
        # in Python 2.7, but it is deprecated
        # pylint:disable=deprecated-method,too-many-locals
        import inspect
        import warnings
        from gevent.monkey import get_original
        # XXX: Very similar to gevent.monkey.patch_module. Should refactor?
        gevent_module = getattr(__import__('gevent.' + mod_name), mod_name)
        module_name = getattr(gevent_module, '__target__', mod_name)

        funcs_given = True
        if not func_names:
            funcs_given = False
            func_names = getattr(gevent_module, '__implements__')

        for func_name in func_names:
            if func_name in exclude:
                continue
            gevent_func = getattr(gevent_module, func_name)
            if not inspect.isfunction(gevent_func) and not funcs_given:
                continue

            func = get_original(module_name, func_name)

            try:
                with warnings.catch_warnings():
                    try:
                        getfullargspec = inspect.getfullargspec
                    except AttributeError:
                        warnings.simplefilter("ignore")
                        getfullargspec = inspect.getargspec
                    gevent_sig = getfullargspec(gevent_func)
                    sig = getfullargspec(func)
            except TypeError:
                if funcs_given:
                    raise
                # Can't do this one. If they specifically asked for it,
                # it's an error, otherwise it's not.
                # Python 3 can check a lot more than Python 2 can.
                continue
            self.assertEqual(sig.args, gevent_sig.args, func_name)
            # The next two might not actually matter?
            self.assertEqual(sig.varargs, gevent_sig.varargs, func_name)
            self.assertEqual(sig.defaults, gevent_sig.defaults, func_name)
            if hasattr(sig, 'keywords'): # the old version
                msg = (func_name, sig.keywords, gevent_sig.keywords)
                try:
                    self.assertEqual(sig.keywords, gevent_sig.keywords, msg)
                except AssertionError:
                    # Ok, if we take `kwargs` and the original function doesn't,
                    # that's OK. We have to do that as a compatibility hack sometimes to
                    # work across multiple python versions.
                    self.assertIsNone(sig.keywords, msg)
                    self.assertEqual('kwargs', gevent_sig.keywords)
            else:
                # The new hotness. Unfortunately, we can't actually check these things
                # until we drop Python 2 support from the shared code. The only known place
                # this is a problem is python 3.11 socket.create_connection(), which we manually
                # ignore. So the checks all pass as is.
                self.assertEqual(sig.kwonlyargs, gevent_sig.kwonlyargs, func_name)
                self.assertEqual(sig.kwonlydefaults, gevent_sig.kwonlydefaults, func_name)
            # Should deal with others: https://docs.python.org/3/library/inspect.html#inspect.getfullargspec

    def assertEqualFlakyRaceCondition(self, a, b):
        try:
            self.assertEqual(a, b)
        except AssertionError:
            flaky.reraiseFlakyTestRaceCondition()

    def assertStartsWith(self, it, has_prefix):
        self.assertTrue(it.startswith(has_prefix), (it, has_prefix))

    def assertNotMonkeyPatched(self):
        from gevent import monkey
        self.assertFalse(monkey.is_anything_patched())
