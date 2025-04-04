# Copyright (c) 2009 AG Projects
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

import re
import time
import unittest

import gevent.testing as greentest
import gevent.testing.timing

import gevent
from gevent import socket
from gevent.hub import Waiter, get_hub
from gevent._compat import NativeStrIO
from gevent._compat import get_this_psutil_process

DELAY = 0.1


class TestCloseSocketWhilePolling(greentest.TestCase):

    def test(self):
        sock = socket.socket()
        self._close_on_teardown(sock)
        t = get_hub().loop.timer(0)
        t.start(sock.close)
        with self.assertRaises(socket.error):
            try:
                sock.connect(('python.org', 81))
            finally:
                t.close()

        gevent.sleep(0)


class TestExceptionInMainloop(greentest.TestCase):

    def test_sleep(self):
        # even if there was an error in the mainloop, the hub should continue to work
        start = time.time()
        gevent.sleep(DELAY)
        delay = time.time() - start

        delay_range = DELAY * 0.9
        self.assertTimeWithinRange(delay, DELAY - delay_range, DELAY + delay_range)

        error = greentest.ExpectedException('TestExceptionInMainloop.test_sleep/fail')

        def fail():
            raise error

        with get_hub().loop.timer(0.001) as t:
            t.start(fail)

            self.expect_one_error()

            start = time.time()
            gevent.sleep(DELAY)
            delay = time.time() - start

            self.assert_error(value=error)
            self.assertTimeWithinRange(delay, DELAY - delay_range, DELAY + delay_range)



class TestSleep(gevent.testing.timing.AbstractGenericWaitTestCase):

    def wait(self, timeout):
        gevent.sleep(timeout)

    def test_simple(self):
        gevent.sleep(0)


class TestWaiterGet(gevent.testing.timing.AbstractGenericWaitTestCase):

    def setUp(self):
        super(TestWaiterGet, self).setUp()
        self.waiter = Waiter()

    def wait(self, timeout):
        with get_hub().loop.timer(timeout) as evt:
            evt.start(self.waiter.switch, None)
            return self.waiter.get()


class TestWaiter(greentest.TestCase):

    def test(self):
        waiter = Waiter()
        self.assertEqual(str(waiter), '<Waiter greenlet=None>')
        waiter.switch(25)
        self.assertEqual(str(waiter), '<Waiter greenlet=None value=25>')
        self.assertEqual(waiter.get(), 25)

        waiter = Waiter()
        waiter.throw(ZeroDivisionError)
        assert re.match('^<Waiter greenlet=None exc_info=.*ZeroDivisionError.*$', str(waiter)), str(waiter)
        self.assertRaises(ZeroDivisionError, waiter.get)

        waiter = Waiter()
        g = gevent.spawn(waiter.get)
        g.name = 'AName'
        gevent.sleep(0)
        str_waiter = str(waiter)
        self.assertTrue(str_waiter.startswith('<Waiter greenlet=<Greenlet "AName'),
                        str_waiter)

        g.kill()


@greentest.skipOnCI("Racy on CI")
class TestPeriodicMonitoringThread(greentest.TestCase):

    def _reset_hub(self):
        hub = get_hub()
        try:
            del hub.exception_stream
        except AttributeError:
            pass
        if hub._threadpool is not None:
            hub.threadpool.join()
            hub.threadpool.kill()
            del hub.threadpool


    def setUp(self):
        super(TestPeriodicMonitoringThread, self).setUp()
        self.monitor_thread = gevent.config.monitor_thread
        gevent.config.monitor_thread = True
        from gevent.monkey import get_original
        self.lock = get_original('threading', 'Lock')()
        self.monitor_fired = 0
        self.monitored_hubs = set()
        self._reset_hub()

    def tearDown(self):
        hub = get_hub()
        if not self.monitor_thread and hub.periodic_monitoring_thread:
            # If it was true, nothing to do. If it was false, tear things down.
            hub.periodic_monitoring_thread.kill()
            hub.periodic_monitoring_thread = None
        gevent.config.monitor_thread = self.monitor_thread
        self.monitored_hubs = None
        self._reset_hub()
        super(TestPeriodicMonitoringThread, self).tearDown()

    def _monitor(self, hub):
        with self.lock:
            self.monitor_fired += 1
            if self.monitored_hubs is not None:
                self.monitored_hubs.add(hub)

    def test_config(self):
        self.assertEqual(0.1, gevent.config.max_blocking_time)

    def _run_monitoring_threads(self, monitor, kill=True):
        self.assertTrue(monitor.should_run)
        from threading import Condition
        cond = Condition()
        cond.acquire()

        def monitor_cond(_hub):
            cond.acquire()
            cond.notify_all()
            cond.release()
            if kill:
                # Only run once. Especially helpful on PyPy, where
                # formatting stacks is expensive.
                monitor.kill()

        monitor.add_monitoring_function(monitor_cond, 0.01)

        cond.wait()
        cond.release()
        monitor.add_monitoring_function(monitor_cond, None)

    @greentest.ignores_leakcheck
    def test_kill_removes_trace(self):
        from greenlet import gettrace
        hub = get_hub()
        hub.start_periodic_monitoring_thread()
        self.assertIsNotNone(gettrace())
        hub.periodic_monitoring_thread.kill()
        self.assertIsNone(gettrace())

    @greentest.ignores_leakcheck
    def test_blocking_this_thread(self):
        hub = get_hub()
        stream = hub.exception_stream = NativeStrIO()
        monitor = hub.start_periodic_monitoring_thread()
        self.assertIsNotNone(monitor)

        basic_monitor_func_count = 1
        if get_this_psutil_process() is not None:
            # psutil is installed
            basic_monitor_func_count += 1

        self.assertEqual(basic_monitor_func_count,
                         len(monitor.monitoring_functions()))
        monitor.add_monitoring_function(self._monitor, 0.1)
        self.assertEqual(basic_monitor_func_count + 1,
                         len(monitor.monitoring_functions()))
        self.assertEqual(self._monitor, monitor.monitoring_functions()[-1].function)
        self.assertEqual(0.1, monitor.monitoring_functions()[-1].period)

        # We must make sure we have switched greenlets at least once,
        # otherwise we can't detect a failure.
        gevent.sleep(hub.loop.approx_timer_resolution)
        assert hub.exception_stream is stream
        try:
            time.sleep(0.3) # Thrice the default
            self._run_monitoring_threads(monitor)
        finally:
            monitor.add_monitoring_function(self._monitor, None)
            self.assertEqual(basic_monitor_func_count,
                             len(monitor._monitoring_functions))
            assert hub.exception_stream is stream
            monitor.kill()
            del hub.exception_stream


        self.assertGreaterEqual(self.monitor_fired, 1)
        data = stream.getvalue()
        self.assertIn('appears to be blocked', data)
        self.assertIn('PeriodicMonitoringThread', data)

    def _prep_worker_thread(self):
        hub = get_hub()
        threadpool = hub.threadpool

        worker_hub = threadpool.apply(get_hub)
        assert hub is not worker_hub
        stream = NativeStrIO()

        # It does not have a monitoring thread yet
        self.assertIsNone(worker_hub.periodic_monitoring_thread)
        # So switch to it and give it one by letting it run.
        # XXX: Python 3.10 appears to have made some changes in the memory model.
        # Specifically, reading values from the background that are set in the
        # background hub *from this thread* is flaky. It takes them awhile to show up.
        # Really, that's correct and expected from a standard C point of view, as we
        # don't insert any memory barriers or things like that. It just always used to
        # work in the past. So now, rather than read them directly, we need to read them
        # from the background thread itself. The same, apparently, goes for
        # writing.
        # Need to figure out what exactly the change was.
        def task():
            get_hub().exception_stream = stream
            gevent.sleep(0.01)
            mon = get_hub().periodic_monitoring_thread
            mon.add_monitoring_function(self._monitor, 0.1)
            return mon
        worker_monitor = threadpool.apply(task)
        self.assertIsNotNone(worker_monitor)

        return worker_hub, stream, worker_monitor

    @greentest.ignores_leakcheck
    def test_blocking_threadpool_thread_task_queue(self):
        # A threadpool thread spends much of its time
        # blocked on the native Lock object. Unless we take
        # care, if that thread had created a hub, it will constantly
        # be reported as blocked.

        worker_hub, stream, worker_monitor = self._prep_worker_thread()

        # Now wait until the monitoring threads have run.
        self._run_monitoring_threads(worker_monitor)
        worker_monitor.kill()

        # We did run the monitor in the worker thread, but it
        # did NOT report itself blocked by the worker thread sitting there.
        with self.lock:
            self.assertIn(worker_hub, self.monitored_hubs)
            self.assertEqual(stream.getvalue(), '')

    @greentest.ignores_leakcheck
    def test_blocking_threadpool_thread_one_greenlet(self):
        # If the background threadpool thread has no other greenlets to run
        # and never switches, then even if it has a hub
        # we don't report it blocking. The threadpool is *meant* to run
        # tasks that block.

        hub = get_hub()
        threadpool = hub.threadpool
        worker_hub, stream, worker_monitor = self._prep_worker_thread()

        task = threadpool.spawn(time.sleep, 0.3)
        # Now wait until the monitoring threads have run.
        self._run_monitoring_threads(worker_monitor)
        # and be sure the task ran
        task.get()
        worker_monitor.kill()

        # We did run the monitor in the worker thread, but it
        # did NOT report itself blocked by the worker thread
        with self.lock:
            self.assertIn(worker_hub, self.monitored_hubs)
            self.assertEqual(stream.getvalue(), '')


    @greentest.ignores_leakcheck
    def test_blocking_threadpool_thread_multi_greenlet(self):
        # If the background threadpool thread ever switches
        # greenlets, monitoring goes into affect.

        hub = get_hub()
        threadpool = hub.threadpool
        worker_hub, stream, worker_monitor = self._prep_worker_thread()

        def task():
            g = gevent.spawn(time.sleep, 0.7)
            g.join()

        task = threadpool.spawn(task)
        # Now wait until the monitoring threads have run.
        self._run_monitoring_threads(worker_monitor, kill=False)
        # and be sure the task ran
        task.get()
        worker_monitor.kill()

        # We did run the monitor in the worker thread, and it
        # DID report itself blocked by the worker thread
        self.assertIn(worker_hub, self.monitored_hubs)
        data = stream.getvalue()
        self.assertIn('appears to be blocked', data)
        self.assertIn('PeriodicMonitoringThread', data)


class TestLoopInterface(unittest.TestCase):

    def test_implemensts_ILoop(self):
        from gevent.testing import verify
        from gevent._interfaces import ILoop

        loop = get_hub().loop

        verify.verifyObject(ILoop, loop)

    def test_callback_implements_ICallback(self):
        from gevent.testing import verify
        from gevent._interfaces import ICallback

        loop = get_hub().loop

        cb = loop.run_callback(lambda: None)
        verify.verifyObject(ICallback, cb)

    def test_callback_ts_implements_ICallback(self):
        from gevent.testing import verify
        from gevent._interfaces import ICallback

        loop = get_hub().loop

        cb = loop.run_callback_threadsafe(lambda: None)
        verify.verifyObject(ICallback, cb)


class TestHandleError(unittest.TestCase):

    def tearDown(self):
        try:
            del get_hub().handle_error
        except AttributeError:
            pass

    def test_exception_in_custom_handle_error_does_not_crash(self):

        def bad_handle_error(*args):
            raise AttributeError

        get_hub().handle_error = bad_handle_error

        class MyException(Exception):
            pass

        def raises():
            raise MyException

        with self.assertRaises(MyException):
            gevent.spawn(raises).get()


if __name__ == '__main__':
    greentest.main()
