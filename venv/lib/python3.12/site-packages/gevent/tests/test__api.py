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

import gevent.testing as greentest
import gevent
from gevent import util, socket

DELAY = 0.1


class Test(greentest.TestCase):

    @greentest.skipOnAppVeyor("Timing causes the state to often be [start,finished]")
    def test_killing_dormant(self):
        state = []

        def test():
            try:
                state.append('start')
                gevent.sleep(DELAY * 3.0)
            except: # pylint:disable=bare-except
                state.append('except')
                # catching GreenletExit

            state.append('finished')

        g = gevent.spawn(test)
        gevent.sleep(DELAY / 2)
        assert state == ['start'], state
        g.kill()
        # will not get there, unless switching is explicitly scheduled by kill
        self.assertEqual(state, ['start', 'except', 'finished'])

    def test_nested_with_timeout(self):
        def func():
            return gevent.with_timeout(0.2, gevent.sleep, 2, timeout_value=1)
        self.assertRaises(gevent.Timeout, gevent.with_timeout, 0.1, func)

    def test_sleep_invalid_switch(self):
        p = gevent.spawn(util.wrap_errors(AssertionError, gevent.sleep), 2)
        gevent.sleep(0)  # wait for p to start, because actual order of switching is reversed
        switcher = gevent.spawn(p.switch, None)
        result = p.get()
        assert isinstance(result, AssertionError), result
        assert 'Invalid switch' in str(result), repr(str(result))
        switcher.kill()

    if hasattr(socket, 'socketpair'):

        def _test_wait_read_invalid_switch(self, sleep):
            sock1, sock2 = socket.socketpair()
            try:
                p = gevent.spawn(util.wrap_errors(AssertionError,
                                                  socket.wait_read), # pylint:disable=no-member
                                 sock1.fileno())
                gevent.get_hub().loop.run_callback(switch_None, p)
                if sleep is not None:
                    gevent.sleep(sleep)
                result = p.get()
                assert isinstance(result, AssertionError), result
                assert 'Invalid switch' in str(result), repr(str(result))
            finally:
                sock1.close()
                sock2.close()

        def test_invalid_switch_None(self):
            self._test_wait_read_invalid_switch(None)

        def test_invalid_switch_0(self):
            self._test_wait_read_invalid_switch(0)

        def test_invalid_switch_1(self):
            self._test_wait_read_invalid_switch(0.001)

        # we don't test wait_write the same way, because socket is always ready to write


def switch_None(g):
    g.switch(None)


class TestTimers(greentest.TestCase):

    def test_timer_fired(self):
        lst = [1]

        def func():
            gevent.spawn_later(0.01, lst.pop)
            gevent.sleep(0.02)

        gevent.spawn(func)
        # Func has not run yet
        self.assertEqual(lst, [1])
        # Run callbacks but don't yield.
        gevent.sleep()

        # Let timers fire. Func should be done.
        gevent.sleep(0.1)
        self.assertEqual(lst, [])


    def test_spawn_is_not_cancelled(self):
        lst = [1]

        def func():
            gevent.spawn(lst.pop)
            # exiting immediately, but self.lst.pop must be called
        gevent.spawn(func)
        gevent.sleep(0.1)
        self.assertEqual(lst, [])


if __name__ == '__main__':
    greentest.main()
