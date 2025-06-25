# Copyright (c) 2008 AG Projects
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

import sys
import gevent.testing as greentest
import weakref
import time
import gc

from gevent import sleep
from gevent import Timeout
from gevent import get_hub


from gevent.testing.timing import SMALL_TICK as DELAY
from gevent.testing import flaky


class Error(Exception):
    pass


class _UpdateNowProxy(object):

    update_now_calls = 0

    def __init__(self, loop):
        self.loop = loop

    def __getattr__(self, name):
        return getattr(self.loop, name)

    def update_now(self):
        self.update_now_calls += 1
        self.loop.update_now()

class _UpdateNowWithTimerProxy(_UpdateNowProxy):

    def timer(self, *_args, **_kwargs):
        return _Timer(self)

class _Timer(object):

    pending = False
    active = False

    def __init__(self, loop):
        self.loop = loop

    def start(self, *_args, **kwargs):
        if kwargs.get("update"):
            self.loop.update_now()
        self.pending = self.active = True

    def stop(self):
        self.active = self.pending = False

    def close(self):
        "Does nothing"


class Test(greentest.TestCase):

    def test_timeout_calls_update_now(self):
        hub = get_hub()
        loop = hub.loop
        proxy = _UpdateNowWithTimerProxy(loop)
        hub.loop = proxy

        try:
            with Timeout(DELAY * 2) as t:
                self.assertTrue(t.pending)
        finally:
            hub.loop = loop

        self.assertEqual(1, proxy.update_now_calls)

    def test_sleep_calls_update_now(self):
        hub = get_hub()
        loop = hub.loop
        proxy = _UpdateNowProxy(loop)
        hub.loop = proxy
        try:
            sleep(0.01)
        finally:
            hub.loop = loop

        self.assertEqual(1, proxy.update_now_calls)


    @greentest.skipOnAppVeyor("Timing is flaky, especially under Py 3.4/64-bit")
    @greentest.skipOnPyPy3OnCI("Timing is flaky, especially under Py 3.4/64-bit")
    @greentest.reraises_flaky_timeout((Timeout, AssertionError))
    def test_api(self):
        # Nothing happens if with-block finishes before the timeout expires
        t = Timeout(DELAY * 2)
        self.assertFalse(t.pending, t)
        with t:
            self.assertTrue(t.pending, t)
            sleep(DELAY)
        # check if timer was actually cancelled
        self.assertFalse(t.pending, t)
        sleep(DELAY * 2)

        # An exception will be raised if it's not
        with self.assertRaises(Timeout) as exc:
            with Timeout(DELAY) as t:
                sleep(DELAY * 10)

        self.assertIs(exc.exception, t)

        # You can customize the exception raised:
        with self.assertRaises(IOError):
            with Timeout(DELAY, IOError("Operation takes way too long")):
                sleep(DELAY * 10)

        # Providing classes instead of values should be possible too:
        with self.assertRaises(ValueError):
            with Timeout(DELAY, ValueError):
                sleep(DELAY * 10)


        try:
            1 / 0
        except ZeroDivisionError:
            with self.assertRaises(ZeroDivisionError):
                with Timeout(DELAY, sys.exc_info()[0]):
                    sleep(DELAY * 10)
                    raise AssertionError('should not get there')
                raise AssertionError('should not get there')
        else:
            raise AssertionError('should not get there')

        # It's possible to cancel the timer inside the block:
        with Timeout(DELAY) as timer:
            timer.cancel()
            sleep(DELAY * 2)

        # To silent the exception before exiting the block, pass False as second parameter.
        XDELAY = 0.1
        start = time.time()
        with Timeout(XDELAY, False):
            sleep(XDELAY * 2)
        delta = time.time() - start
        self.assertTimeWithinRange(delta, 0, XDELAY * 2)

        # passing None as seconds disables the timer
        with Timeout(None):
            sleep(DELAY)
        sleep(DELAY)

    def test_ref(self):
        err = Error()
        err_ref = weakref.ref(err)
        with Timeout(DELAY * 2, err):
            sleep(DELAY)
        del err
        gc.collect()
        self.assertFalse(err_ref(), err_ref)

    @flaky.reraises_flaky_race_condition()
    def test_nested_timeout(self):
        with Timeout(DELAY, False):
            with Timeout(DELAY * 10, False):
                sleep(DELAY * 3 * 20)
            raise AssertionError('should not get there')

        with Timeout(DELAY) as t1:
            with Timeout(DELAY * 20) as t2:
                with self.assertRaises(Timeout) as exc:
                    sleep(DELAY * 30)
                self.assertIs(exc.exception, t1)

                self.assertFalse(t1.pending, t1)
                self.assertTrue(t2.pending, t2)

            self.assertFalse(t2.pending)

        with Timeout(DELAY * 20) as t1:
            with Timeout(DELAY) as t2:
                with self.assertRaises(Timeout) as exc:
                    sleep(DELAY * 30)
                self.assertIs(exc.exception, t2)

                self.assertTrue(t1.pending, t1)
                self.assertFalse(t2.pending, t2)

        self.assertFalse(t1.pending)


if __name__ == '__main__':
    greentest.main()
