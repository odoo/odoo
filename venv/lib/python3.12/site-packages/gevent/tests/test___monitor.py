# Copyright 2018 gevent contributors. See LICENSE for details.

import gc
import unittest


from greenlet import gettrace
from greenlet import settrace

from gevent.monkey import get_original
from gevent._compat import thread_mod_name
from gevent._compat import NativeStrIO

from gevent.testing import verify
from gevent.testing.skipping import skipWithoutPSUtil

from gevent import _monitor as monitor
from gevent import config as GEVENT_CONFIG

get_ident = get_original(thread_mod_name, 'get_ident')

class MockHub(object):
    _threadpool = None
    _resolver = None

    def __init__(self):
        self.thread_ident = get_ident()
        self.exception_stream = NativeStrIO()
        self.dead = False

    def __bool__(self):
        return not self.dead

    __nonzero__ = __bool__

    def handle_error(self, *args): # pylint:disable=unused-argument
        raise # pylint:disable=misplaced-bare-raise

    @property
    def loop(self):
        return self

    def reinit(self):
        "mock loop.reinit"

class _AbstractTestPeriodicMonitoringThread(object):
    # Makes sure we don't actually spin up a new monitoring thread.

    # pylint:disable=no-member

    def setUp(self):
        super(_AbstractTestPeriodicMonitoringThread, self).setUp()
        self._orig_start_new_thread = monitor.start_new_thread
        self._orig_thread_sleep = monitor.thread_sleep
        monitor.thread_sleep = lambda _s: gc.collect() # For PyPy
        self.tid = 0xDEADBEEF
        def start_new_thread(_f, _a):
            r = self.tid
            self.tid += 1
            return r

        monitor.start_new_thread = start_new_thread
        self.hub = MockHub()
        self.pmt = monitor.PeriodicMonitoringThread(self.hub)
        self.hub.periodic_monitoring_thread = self.pmt
        self.pmt_default_funcs = self.pmt.monitoring_functions()[:]
        self.len_pmt_default_funcs = len(self.pmt_default_funcs)

    def tearDown(self):
        monitor.start_new_thread = self._orig_start_new_thread
        monitor.thread_sleep = self._orig_thread_sleep
        prev = self.pmt._greenlet_tracer.previous_trace_function
        self.pmt.kill()
        assert gettrace() is prev, (gettrace(), prev)
        settrace(None)
        super(_AbstractTestPeriodicMonitoringThread, self).tearDown()


class TestPeriodicMonitoringThread(_AbstractTestPeriodicMonitoringThread,
                                   unittest.TestCase):

    def test_constructor(self):
        self.assertEqual(0xDEADBEEF, self.pmt.monitor_thread_ident)
        self.assertEqual(gettrace(), self.pmt._greenlet_tracer)

    @skipWithoutPSUtil("Verifies the process")
    def test_get_process(self):
        proc = self.pmt._get_process()
        self.assertIsNotNone(proc)
        # Same object is returned each time.
        self.assertIs(proc, self.pmt._get_process())

    def test_hub_wref(self):
        self.assertIs(self.hub, self.pmt.hub)
        del self.hub

        gc.collect()
        self.assertIsNone(self.pmt.hub)

        # And it killed itself.
        self.assertFalse(self.pmt.should_run)
        self.assertIsNone(gettrace())


    def test_add_monitoring_function(self):

        self.assertRaises(ValueError, self.pmt.add_monitoring_function, None, 1)
        self.assertRaises(ValueError, self.pmt.add_monitoring_function, lambda: None, -1)

        def f():
            "Does nothing"

        # Add
        self.pmt.add_monitoring_function(f, 1)
        self.assertEqual(self.len_pmt_default_funcs + 1, len(self.pmt.monitoring_functions()))
        self.assertEqual(1, self.pmt.monitoring_functions()[1].period)

        # Update
        self.pmt.add_monitoring_function(f, 2)
        self.assertEqual(self.len_pmt_default_funcs + 1, len(self.pmt.monitoring_functions()))
        self.assertEqual(2, self.pmt.monitoring_functions()[1].period)

        # Remove
        self.pmt.add_monitoring_function(f, None)
        self.assertEqual(self.len_pmt_default_funcs, len(self.pmt.monitoring_functions()))

    def test_calculate_sleep_time(self):
        self.assertEqual(
            self.pmt.monitoring_functions()[0].period,
            self.pmt.calculate_sleep_time())

        # Pretend that GEVENT_CONFIG.max_blocking_time was set to 0,
        # to disable this monitor.
        self.pmt._calculated_sleep_time = 0
        self.assertEqual(
            self.pmt.inactive_sleep_time,
            self.pmt.calculate_sleep_time()
        )

        # Getting the list of monitoring functions will also
        # do this, if it looks like it has changed
        self.pmt.monitoring_functions()[0].period = -1
        self.pmt._calculated_sleep_time = 0
        self.pmt.monitoring_functions()
        self.assertEqual(
            self.pmt.monitoring_functions()[0].period,
            self.pmt.calculate_sleep_time())
        self.assertEqual(
            self.pmt.monitoring_functions()[0].period,
            self.pmt._calculated_sleep_time)

    def test_call_destroyed_hub(self):
        # Add a function that destroys the hub so we break out (eventually)
        # This clears the wref, which eventually calls kill()
        def f(_hub):
            _hub = None
            self.hub = None
            gc.collect()

        self.pmt.add_monitoring_function(f, 0.1)
        self.pmt()
        self.assertFalse(self.pmt.should_run)

    def test_call_dead_hub(self):
        # Add a function that makes the hub go false (e.g., it quit)
        # This causes the function to kill itself.
        def f(hub):
            hub.dead = True
        self.pmt.add_monitoring_function(f, 0.1)
        self.pmt()
        self.assertFalse(self.pmt.should_run)

    def test_call_SystemExit(self):
        # breaks the loop
        def f(_hub):
            raise SystemExit()

        self.pmt.add_monitoring_function(f, 0.1)
        self.pmt()

    def test_call_other_error(self):
        class MyException(Exception):
            pass

        def f(_hub):
            raise MyException()

        self.pmt.add_monitoring_function(f, 0.1)
        with self.assertRaises(MyException):
            self.pmt()

    def test_hub_reinit(self):
        import os
        from gevent.hub import reinit
        self.pmt.pid = -1
        old_tid = self.pmt.monitor_thread_ident

        reinit(self.hub)

        self.assertEqual(os.getpid(), self.pmt.pid)
        self.assertEqual(old_tid + 1, self.pmt.monitor_thread_ident)



class TestPeriodicMonitorBlocking(_AbstractTestPeriodicMonitoringThread,
                                  unittest.TestCase):

    def test_previous_trace(self):
        self.pmt.kill()
        self.assertIsNone(gettrace())

        called = []
        def f(*args):
            called.append(args)

        settrace(f)

        self.pmt = monitor.PeriodicMonitoringThread(self.hub)
        self.assertEqual(gettrace(), self.pmt._greenlet_tracer)
        self.assertIs(self.pmt._greenlet_tracer.previous_trace_function, f)

        self.pmt._greenlet_tracer('event', ('args',))

        self.assertEqual([('event', ('args',))], called)

    def test__greenlet_tracer(self):
        self.assertEqual(0, self.pmt._greenlet_tracer.greenlet_switch_counter)
        # Unknown event still counts as a switch (should it?)
        self.pmt._greenlet_tracer('unknown', None)
        self.assertEqual(1, self.pmt._greenlet_tracer.greenlet_switch_counter)
        self.assertIsNone(self.pmt._greenlet_tracer.active_greenlet)

        origin = object()
        target = object()

        self.pmt._greenlet_tracer('switch', (origin, target))
        self.assertEqual(2, self.pmt._greenlet_tracer.greenlet_switch_counter)
        self.assertIs(target, self.pmt._greenlet_tracer.active_greenlet)

        # Unknown event removes active greenlet
        self.pmt._greenlet_tracer('unknown', ())
        self.assertEqual(3, self.pmt._greenlet_tracer.greenlet_switch_counter)
        self.assertIsNone(self.pmt._greenlet_tracer.active_greenlet)

    def test_monitor_blocking(self):
        # Initially there's no active greenlet and no switches,
        # so nothing is considered blocked
        from gevent.events import subscribers
        from gevent.events import IEventLoopBlocked
        events = []
        subscribers.append(events.append)

        self.assertFalse(self.pmt.monitor_blocking(self.hub))

        # Give it an active greenlet
        origin = object()
        target = object()
        self.pmt._greenlet_tracer('switch', (origin, target))

        # We've switched, so we're not blocked
        self.assertFalse(self.pmt.monitor_blocking(self.hub))
        self.assertFalse(events)

        # Again without switching is a problem.
        self.assertTrue(self.pmt.monitor_blocking(self.hub))
        self.assertTrue(events)
        verify.verifyObject(IEventLoopBlocked, events[0])
        del events[:]

        # But we can order it not to be a problem
        self.pmt.ignore_current_greenlet_blocking()
        self.assertFalse(self.pmt.monitor_blocking(self.hub))
        self.assertFalse(events)

        # And back again
        self.pmt.monitor_current_greenlet_blocking()
        self.assertTrue(self.pmt.monitor_blocking(self.hub))

        # A bad thread_ident in the hub doesn't mess things up
        self.hub.thread_ident = -1
        self.assertTrue(self.pmt.monitor_blocking(self.hub))


class MockProcess(object):

    def __init__(self, rss):
        self.rss = rss

    def memory_full_info(self):
        return self


@skipWithoutPSUtil("Accessess memory info")
class TestPeriodicMonitorMemory(_AbstractTestPeriodicMonitoringThread,
                                unittest.TestCase):

    rss = 0

    def setUp(self):
        _AbstractTestPeriodicMonitoringThread.setUp(self)
        self._old_max = GEVENT_CONFIG.max_memory_usage
        GEVENT_CONFIG.max_memory_usage = None

        self.pmt._get_process = lambda: MockProcess(self.rss)

    def tearDown(self):
        GEVENT_CONFIG.max_memory_usage = self._old_max
        _AbstractTestPeriodicMonitoringThread.tearDown(self)

    def test_can_monitor_and_install(self):
        # We run tests with psutil installed, and we have access to our
        # process.
        self.assertTrue(self.pmt.can_monitor_memory_usage())
        # No warning, adds a function

        self.pmt.install_monitor_memory_usage()
        self.assertEqual(self.len_pmt_default_funcs + 1, len(self.pmt.monitoring_functions()))

    def test_cannot_monitor_and_install(self):
        import warnings
        self.pmt._get_process = lambda: None
        self.assertFalse(self.pmt.can_monitor_memory_usage())

        # This emits a warning, visible by default
        with warnings.catch_warnings(record=True) as ws:
            self.pmt.install_monitor_memory_usage()

        self.assertEqual(1, len(ws))
        self.assertIs(monitor.MonitorWarning, ws[0].category)

    def test_monitor_no_allowed(self):
        self.assertEqual(-1, self.pmt.monitor_memory_usage(None))

    def test_monitor_greater(self):
        from gevent import events

        self.rss = 2
        GEVENT_CONFIG.max_memory_usage = 1

        # Initial event
        event = self.pmt.monitor_memory_usage(None)
        self.assertIsInstance(event, events.MemoryUsageThresholdExceeded)
        self.assertEqual(2, event.mem_usage)
        self.assertEqual(1, event.max_allowed) # pylint:disable=no-member
        self.assertIsInstance(event.memory_info, MockProcess) # pylint:disable=no-member

        # No growth, no event
        event = self.pmt.monitor_memory_usage(None)
        self.assertIsNone(event)

        # Growth, event
        self.rss = 3
        event = self.pmt.monitor_memory_usage(None)
        self.assertIsInstance(event, events.MemoryUsageThresholdExceeded)
        self.assertEqual(3, event.mem_usage)

        # Shrinking below gets us back
        self.rss = 1
        event = self.pmt.monitor_memory_usage(None)
        self.assertIsInstance(event, events.MemoryUsageUnderThreshold)
        self.assertEqual(1, event.mem_usage)

        # coverage
        repr(event)

        # No change, no event
        event = self.pmt.monitor_memory_usage(None)
        self.assertIsNone(event)

        # Growth, event
        self.rss = 3
        event = self.pmt.monitor_memory_usage(None)
        self.assertIsInstance(event, events.MemoryUsageThresholdExceeded)
        self.assertEqual(3, event.mem_usage)


    def test_monitor_initial_below(self):
        self.rss = 1
        GEVENT_CONFIG.max_memory_usage = 10


        event = self.pmt.monitor_memory_usage(None)
        self.assertIsNone(event)

if __name__ == '__main__':
    unittest.main()
