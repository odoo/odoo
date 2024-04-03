# Copyright (c) 2008-2009 AG Projects
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
import functools
import unittest

import gevent.testing as greentest
import gevent

from gevent import sleep, with_timeout, getcurrent
from gevent import greenlet
from gevent.event import AsyncResult
from gevent.queue import Queue, Channel

from gevent.testing.timing import AbstractGenericWaitTestCase
from gevent.testing.timing import AbstractGenericGetTestCase
from gevent.testing import timing
from gevent.testing import ignores_leakcheck

DELAY = timing.SMALL_TICK
greentest.TestCase.error_fatal = False


class ExpectedError(greentest.ExpectedException):
    pass

class ExpectedJoinError(ExpectedError):
    pass

class SuiteExpectedException(ExpectedError):
    pass

class GreenletRaisesJoin(gevent.Greenlet):
    killed = False
    joined = False
    raise_on_join = True

    def join(self, timeout=None):
        self.joined += 1
        if self.raise_on_join:
            raise ExpectedJoinError
        return gevent.Greenlet.join(self, timeout)

    def kill(self, *args, **kwargs): # pylint:disable=signature-differs
        self.killed += 1
        return gevent.Greenlet.kill(self, *args, **kwargs)

class TestLink(greentest.TestCase):

    def test_link_to_asyncresult(self):
        p = gevent.spawn(lambda: 100)
        event = AsyncResult()
        p.link(event)
        self.assertEqual(event.get(), 100)

        for _ in range(3):
            event2 = AsyncResult()
            p.link(event2)
            self.assertEqual(event2.get(), 100)

    def test_link_to_asyncresult_exception(self):
        err = ExpectedError('test_link_to_asyncresult_exception')
        p = gevent.spawn(lambda: getcurrent().throw(err))
        event = AsyncResult()
        p.link(event)
        with self.assertRaises(ExpectedError) as exc:
            event.get()

        self.assertIs(exc.exception, err)

        for _ in range(3):
            event2 = AsyncResult()
            p.link(event2)
            with self.assertRaises(ExpectedError) as exc:
                event2.get()
            self.assertIs(exc.exception, err)

    def test_link_to_queue(self):
        p = gevent.spawn(lambda: 100)
        q = Queue()
        p.link(q.put)
        self.assertEqual(q.get().get(), 100)

        for _ in range(3):
            p.link(q.put)
            self.assertEqual(q.get().get(), 100)

    def test_link_to_channel(self):
        p1 = gevent.spawn(lambda: 101)
        p2 = gevent.spawn(lambda: 102)
        p3 = gevent.spawn(lambda: 103)
        q = Channel()
        p1.link(q.put)
        p2.link(q.put)
        p3.link(q.put)
        results = [q.get().get(), q.get().get(), q.get().get()]
        self.assertEqual(sorted(results), [101, 102, 103], results)


class TestUnlink(greentest.TestCase):
    switch_expected = False

    def _test_func(self, p, link):
        link(dummy_test_func)
        self.assertEqual(1, p.has_links())

        p.unlink(dummy_test_func)
        self.assertEqual(0, p.has_links())

        link(self.setUp)
        self.assertEqual(1, p.has_links())

        p.unlink(self.setUp)
        self.assertEqual(0, p.has_links())

        p.kill()

    def test_func_link(self):
        p = gevent.spawn(dummy_test_func)
        self._test_func(p, p.link)

    def test_func_link_value(self):
        p = gevent.spawn(dummy_test_func)
        self._test_func(p, p.link_value)

    def test_func_link_exception(self):
        p = gevent.spawn(dummy_test_func)
        self._test_func(p, p.link_exception)


class LinksTestCase(greentest.TestCase):

    link_method = None

    def link(self, p, listener=None):
        getattr(p, self.link_method)(listener)

    def set_links(self, p):
        event = AsyncResult()
        self.link(p, event)

        queue = Queue(1)
        self.link(p, queue.put)

        callback_flag = ['initial']
        self.link(p, lambda *args: callback_flag.remove('initial'))

        for _ in range(10):
            self.link(p, AsyncResult())
            self.link(p, Queue(1).put)

        return event, queue, callback_flag

    def set_links_timeout(self, link):
        # stuff that won't be touched
        event = AsyncResult()
        link(event)

        queue = Channel()
        link(queue.put)
        return event, queue

    def check_timed_out(self, event, queue):
        got = with_timeout(DELAY, event.get, timeout_value=X)
        self.assertIs(got, X)
        got = with_timeout(DELAY, queue.get, timeout_value=X)
        self.assertIs(got, X)


def return25():
    return 25



class TestReturn_link(LinksTestCase):
    link_method = 'link'

    p = None

    def cleanup(self):
        self.p.unlink_all()
        self.p = None

    def test_return(self):
        self.p = gevent.spawn(return25)
        for _ in range(3):
            self._test_return(self.p, 25)
        self.p.kill()

    def _test_return(self, p, result):
        event, queue, callback_flag = self.set_links(p)

        # stuff that will time out because there's no unhandled exception:
        xxxxx = self.set_links_timeout(p.link_exception)

        sleep(DELAY * 2)
        self.assertFalse(p)

        self.assertEqual(event.get(), result)
        self.assertEqual(queue.get().get(), result)

        sleep(DELAY)
        self.assertFalse(callback_flag)

        self.check_timed_out(*xxxxx)

    def _test_kill(self, p):
        event, queue, callback_flag = self.set_links(p)
        xxxxx = self.set_links_timeout(p.link_exception)

        p.kill()
        sleep(DELAY)
        self.assertFalse(p)


        self.assertIsInstance(event.get(), gevent.GreenletExit)
        self.assertIsInstance(queue.get().get(), gevent.GreenletExit)

        sleep(DELAY)
        self.assertFalse(callback_flag)

        self.check_timed_out(*xxxxx)

    def test_kill(self):
        p = self.p = gevent.spawn(sleep, DELAY)
        for _ in range(3):
            self._test_kill(p)


class TestReturn_link_value(TestReturn_link):
    link_method = 'link_value'


class TestRaise_link(LinksTestCase):
    link_method = 'link'

    def _test_raise(self, p):
        event, queue, callback_flag = self.set_links(p)
        xxxxx = self.set_links_timeout(p.link_value)

        sleep(DELAY)
        self.assertFalse(p, p)

        self.assertRaises(ExpectedError, event.get)
        self.assertEqual(queue.get(), p)
        sleep(DELAY)
        self.assertFalse(callback_flag, callback_flag)

        self.check_timed_out(*xxxxx)

    def test_raise(self):
        p = gevent.spawn(lambda: getcurrent().throw(ExpectedError('test_raise')))
        for _ in range(3):
            self._test_raise(p)


class TestRaise_link_exception(TestRaise_link):
    link_method = 'link_exception'


class TestStuff(greentest.TestCase):

    def test_minimal_id(self):
        g = gevent.spawn(lambda: 1)
        self.assertGreaterEqual(g.minimal_ident, 0)
        self.assertGreaterEqual(g.parent.minimal_ident, 0)
        g.join() # don't leave dangling, breaks the leak checks

    def test_wait_noerrors(self):
        x = gevent.spawn(lambda: 1)
        y = gevent.spawn(lambda: 2)
        z = gevent.spawn(lambda: 3)
        gevent.joinall([x, y, z], raise_error=True)
        self.assertEqual([x.value, y.value, z.value], [1, 2, 3])
        e = AsyncResult()
        x.link(e)
        self.assertEqual(e.get(), 1)
        x.unlink(e)
        e = AsyncResult()
        x.link(e)
        self.assertEqual(e.get(), 1)

    @ignores_leakcheck
    def test_wait_error(self):

        def x():
            sleep(DELAY)
            return 1
        x = gevent.spawn(x)
        y = gevent.spawn(lambda: getcurrent().throw(ExpectedError('test_wait_error')))
        self.assertRaises(ExpectedError, gevent.joinall, [x, y], raise_error=True)
        self.assertRaises(ExpectedError, gevent.joinall, [y], raise_error=True)
        x.join()

    @ignores_leakcheck
    def test_joinall_exception_order(self):
        # if there're several exceptions raised, the earliest one must be raised by joinall
        def first():
            sleep(0.1)
            raise ExpectedError('first')
        a = gevent.spawn(first)
        b = gevent.spawn(lambda: getcurrent().throw(ExpectedError('second')))
        with self.assertRaisesRegex(ExpectedError, 'second'):
            gevent.joinall([a, b], raise_error=True)

        gevent.joinall([a, b])

    def test_joinall_count_raise_error(self):
        # When joinall is asked not to raise an error, the 'count' param still
        # works.
        def raises_but_ignored():
            raise ExpectedError("count")

        def sleep_forever():
            while True:
                sleep(0.1)

        sleeper = gevent.spawn(sleep_forever)
        raiser = gevent.spawn(raises_but_ignored)

        gevent.joinall([sleeper, raiser], raise_error=False, count=1)
        self.assert_greenlet_ready(raiser)
        self.assert_greenlet_not_ready(sleeper)

        # Clean up our mess
        sleeper.kill()
        self.assert_greenlet_ready(sleeper)

    def test_multiple_listeners_error(self):
        # if there was an error while calling a callback
        # it should not prevent the other listeners from being called
        # also, all of the errors should be logged, check the output
        # manually that they are
        p = gevent.spawn(lambda: 5)
        results = []

        def listener1(*_args):
            results.append(10)
            raise ExpectedError('listener1')

        def listener2(*_args):
            results.append(20)
            raise ExpectedError('listener2')

        def listener3(*_args):
            raise ExpectedError('listener3')

        p.link(listener1)
        p.link(listener2)
        p.link(listener3)
        sleep(DELAY * 10)
        self.assertIn(results, [[10, 20], [20, 10]])

        p = gevent.spawn(lambda: getcurrent().throw(ExpectedError('test_multiple_listeners_error')))
        results = []
        p.link(listener1)
        p.link(listener2)
        p.link(listener3)
        sleep(DELAY * 10)
        self.assertIn(results, [[10, 20], [20, 10]])

    class Results(object):

        def __init__(self):
            self.results = []

        def listener1(self, p):
            p.unlink(self.listener2)
            self.results.append(5)
            raise ExpectedError('listener1')

        def listener2(self, p):
            p.unlink(self.listener1)
            self.results.append(5)
            raise ExpectedError('listener2')

        def listener3(self, _p):
            raise ExpectedError('listener3')

    def _test_multiple_listeners_error_unlink(self, _p, link):
        # notification must not happen after unlink even
        # though notification process has been already started
        results = self.Results()

        link(results.listener1)
        link(results.listener2)
        link(results.listener3)
        sleep(DELAY * 10)
        self.assertEqual([5], results.results)


    def test_multiple_listeners_error_unlink_Greenlet_link(self):
        p = gevent.spawn(lambda: 5)
        self._test_multiple_listeners_error_unlink(p, p.link)
        p.kill()

    def test_multiple_listeners_error_unlink_Greenlet_rawlink(self):
        p = gevent.spawn(lambda: 5)
        self._test_multiple_listeners_error_unlink(p, p.rawlink)

    def test_multiple_listeners_error_unlink_AsyncResult_rawlink(self):
        e = AsyncResult()
        gevent.spawn(e.set, 6)
        self._test_multiple_listeners_error_unlink(e, e.rawlink)


def dummy_test_func(*_args):
    pass


class A(object):

    def method(self):
        pass

class Subclass(gevent.Greenlet):
    pass

class TestStr(greentest.TestCase):

    def test_function(self):
        g = gevent.Greenlet.spawn(dummy_test_func)
        self.assert_nstr_endswith(g, 'at X: dummy_test_func>')
        self.assert_greenlet_not_ready(g)
        g.join()
        self.assert_greenlet_ready(g)
        self.assert_nstr_endswith(g, 'at X: dummy_test_func>')


    def test_method(self):
        g = gevent.Greenlet.spawn(A().method)
        self.assert_nstr_startswith(g, '<Greenlet at X:')

        # Accessing the name to generate a minimal_ident will cause it to be included.
        getattr(g, 'name')
        self.assert_nstr_startswith(g, '<Greenlet "Greenlet-')

        # Assigning to the name changes it
        g.name = 'Foo'
        self.assert_nstr_startswith(g, '<Greenlet "Foo"')

        self.assert_nstr_endswith(g, 'at X: <bound method A.method of <module.A object at X>>>')
        self.assert_greenlet_not_ready(g)
        g.join()
        self.assert_greenlet_ready(g)
        self.assert_nstr_endswith(g, 'at X: <bound method A.method of <module.A object at X>>>')

    def test_subclass(self):
        g = Subclass()
        self.assert_nstr_startswith(g, '<Subclass ')
        self.assert_nstr_endswith(g, 'at X: _run>')

        g = Subclass(None, 'question', answer=42)
        self.assert_nstr_endswith(g, " at X: _run('question', answer=42)>")


class TestJoin(AbstractGenericWaitTestCase):

    def wait(self, timeout):
        g = gevent.spawn(gevent.sleep, 10)
        try:
            return g.join(timeout=timeout)
        finally:
            g.kill()


class TestGet(AbstractGenericGetTestCase):

    def wait(self, timeout):
        g = gevent.spawn(gevent.sleep, 10)
        try:
            return g.get(timeout=timeout)
        finally:
            g.kill()


class TestJoinAll0(AbstractGenericWaitTestCase):

    g = gevent.Greenlet()

    def wait(self, timeout):
        gevent.joinall([self.g], timeout=timeout)


class TestJoinAll(AbstractGenericWaitTestCase):

    def wait(self, timeout):
        g = gevent.spawn(gevent.sleep, 10)
        try:
            gevent.joinall([g], timeout=timeout)
        finally:
            g.kill()


class TestBasic(greentest.TestCase):

    def test_spawn_non_callable(self):
        self.assertRaises(TypeError, gevent.spawn, 1)
        self.assertRaises(TypeError, gevent.spawn_raw, 1)

        # Not passing the run argument, just the seconds argument
        self.assertRaises(TypeError, gevent.spawn_later, 1)
        # Passing both, but not implemented
        self.assertRaises(TypeError, gevent.spawn_later, 1, 1)

    def test_spawn_raw_kwargs(self):
        value = []

        def f(*args, **kwargs):
            value.append(args)
            value.append(kwargs)

        g = gevent.spawn_raw(f, 1, name='value')
        gevent.sleep(0.01)
        self.assertFalse(g)
        self.assertEqual(value[0], (1,))
        self.assertEqual(value[1], {'name': 'value'})

    def test_simple_exit(self):
        link_test = []

        def func(delay, return_value=4):
            gevent.sleep(delay)
            return return_value

        g = gevent.Greenlet(func, 0.01, return_value=5)
        g.rawlink(link_test.append) # use rawlink to avoid timing issues on Appveyor/Travis (not always successful)
        self.assertFalse(g, g)
        self.assertFalse(g.dead, g)
        self.assertFalse(g.started, g)
        self.assertFalse(g.ready(), g)
        self.assertFalse(g.successful(), g)
        self.assertIsNone(g.value, g)
        self.assertIsNone(g.exception, g)

        g.start()
        self.assertTrue(g, g) # changed
        self.assertFalse(g.dead, g)
        self.assertTrue(g.started, g) # changed
        self.assertFalse(g.ready(), g)
        self.assertFalse(g.successful(), g)
        self.assertIsNone(g.value, g)
        self.assertIsNone(g.exception, g)

        gevent.sleep(0.001)
        self.assertTrue(g)
        self.assertFalse(g.dead, g)
        self.assertTrue(g.started, g)
        self.assertFalse(g.ready(), g)
        self.assertFalse(g.successful(), g)
        self.assertIsNone(g.value, g)
        self.assertIsNone(g.exception, g)
        self.assertFalse(link_test)

        gevent.sleep(0.02)
        self.assertFalse(g, g) # changed
        self.assertTrue(g.dead, g) # changed
        self.assertFalse(g.started, g) # changed
        self.assertTrue(g.ready(), g) # changed
        self.assertTrue(g.successful(), g) # changed
        self.assertEqual(g.value, 5) # changed
        self.assertIsNone(g.exception, g)

        self._check_flaky_eq(link_test, g)

    def _check_flaky_eq(self, link_test, g):
        if not greentest.RUNNING_ON_CI:
            # TODO: Change this to assertEqualFlakyRaceCondition and figure
            # out what the CI issue is.
            self.assertEqual(link_test, [g]) # changed

    def test_error_exit(self):
        link_test = []

        def func(delay, return_value=4):
            gevent.sleep(delay)
            error = ExpectedError('test_error_exit')
            setattr(error, 'myattr', return_value)
            raise error

        g = gevent.Greenlet(func, timing.SMALLEST_RELIABLE_DELAY, return_value=5)
        # use rawlink to avoid timing issues on Appveyor (not always successful)
        g.rawlink(link_test.append)
        g.start()
        gevent.sleep()
        gevent.sleep(timing.LARGE_TICK)
        self.assertFalse(g)
        self.assertTrue(g.dead)
        self.assertFalse(g.started)
        self.assertTrue(g.ready())
        self.assertFalse(g.successful())
        self.assertIsNone(g.value) # not changed
        self.assertEqual(g.exception.myattr, 5)
        self._check_flaky_eq(link_test, g)

    def test_exc_info_no_error(self):
        # Before running
        self.assertFalse(greenlet.Greenlet().exc_info)
        g = greenlet.Greenlet(gevent.sleep)
        g.start()
        g.join()
        self.assertFalse(g.exc_info)

    @greentest.skipOnCI(
        "Started getting a Fatal Python error on "
        "Github Actions on 2020-12-18, even with recursion limits "
        "in place. It was fine before that."
    )
    def test_recursion_error(self):
        # https://github.com/gevent/gevent/issues/1704
        # A RuntimeError: recursion depth exceeded
        # does not break things.
        #
        # However, sometimes, on some interpreter versions on some
        # systems, actually exhausting the stack results in "Fatal
        # Python error: Cannot recover from stack overflow.". So we
        # need to use a low recursion limit so that doesn't happen.
        # Doesn't seem to help though.
        # See https://github.com/gevent/gevent/runs/1577692901?check_suite_focus=true#step:21:46
        import sys
        limit = sys.getrecursionlimit()
        self.addCleanup(sys.setrecursionlimit, limit)
        sys.setrecursionlimit(limit // 4)
        def recur():
            recur() # This is expected to raise RecursionError

        errors = []
        def handle_error(glet, t, v, tb):
            errors.append((glet, t, v, tb))

        try:
            gevent.get_hub().handle_error = handle_error

            g = gevent.spawn(recur)
            def wait():
                return gevent.joinall([g])

            g2 = gevent.spawn(wait)

            gevent.joinall([g2])
        finally:
            del gevent.get_hub().handle_error

        try:
            expected_exc = RecursionError
        except NameError:
            expected_exc = RuntimeError
        with self.assertRaises(expected_exc):
            g.get()

        self.assertFalse(g.successful())
        self.assertTrue(g.dead)

        self.assertTrue(errors)
        self.assertEqual(1, len(errors))
        self.assertIs(errors[0][0], g)
        self.assertEqual(errors[0][1], expected_exc)
        del errors[:]


    def test_tree_locals(self):
        g = g2 = None
        def func():
            child = greenlet.Greenlet()
            self.assertIs(child.spawn_tree_locals, getcurrent().spawn_tree_locals)
            self.assertIs(child.spawning_greenlet(), getcurrent())
        g = greenlet.Greenlet(func)
        g2 = greenlet.Greenlet(func)
        # Creating those greenlets did not give the main greenlet
        # a locals dict.
        self.assertFalse(hasattr(getcurrent(), 'spawn_tree_locals'),
                         getcurrent())
        self.assertIsNot(g.spawn_tree_locals, g2.spawn_tree_locals)
        g.start()
        g.join()

        raw = gevent.spawn_raw(func)
        self.assertIsNotNone(raw.spawn_tree_locals)
        self.assertIsNot(raw.spawn_tree_locals, g.spawn_tree_locals)
        self.assertIs(raw.spawning_greenlet(), getcurrent())
        while not raw.dead:
            gevent.sleep(0.01)

    def test_add_spawn_callback(self):
        called = {'#': 0}

        def cb(gr):
            called['#'] += 1
            gr._called_test = True

        gevent.Greenlet.add_spawn_callback(cb)
        try:
            g = gevent.spawn(lambda: None)
            self.assertTrue(hasattr(g, '_called_test'))
            g.join()
            self.assertEqual(called['#'], 1)

            g = gevent.spawn_later(1e-5, lambda: None)
            self.assertTrue(hasattr(g, '_called_test'))
            g.join()
            self.assertEqual(called['#'], 2)

            g = gevent.Greenlet(lambda: None)
            g.start()
            self.assertTrue(hasattr(g, '_called_test'))
            g.join()
            self.assertEqual(called['#'], 3)

            gevent.Greenlet.remove_spawn_callback(cb)
            g = gevent.spawn(lambda: None)
            self.assertFalse(hasattr(g, '_called_test'))
            g.join()
            self.assertEqual(called['#'], 3)
        finally:
            gevent.Greenlet.remove_spawn_callback(cb)

    def test_getframe_value_error(self):
        def get():
            raise ValueError("call stack is not deep enough")
        try:
            ogf = greenlet.sys_getframe
        except AttributeError: # pragma: no cover
            # Must be running cython compiled
            raise unittest.SkipTest("Cannot mock when Cython compiled")
        greenlet.sys_getframe = get
        try:
            child = greenlet.Greenlet()
            self.assertIsNone(child.spawning_stack)
        finally:
            greenlet.sys_getframe = ogf

    def test_minimal_ident_parent_not_hub(self):

        g = gevent.spawn(lambda: 1)
        self.assertIs(g.parent, gevent.get_hub())
        g.parent = getcurrent()
        try:
            self.assertIsNot(g.parent, gevent.get_hub())

            with self.assertRaisesRegex((TypeError, # Cython
                                         AttributeError), # PyPy
                                        'Cannot convert|ident_registry'):
                getattr(g, 'minimal_ident')
        finally:
            # Attempting to switch into this later, when we next cycle the
            # loop, would raise an InvalidSwitchError if we don't put
            # things back the way they were (or kill the greenlet)
            g.parent = gevent.get_hub()
            g.kill()


class TestKill(greentest.TestCase):

    def __assertKilled(self, g, successful):
        self.assertFalse(g)
        self.assertTrue(g.dead)
        self.assertFalse(g.started)
        self.assertTrue(g.ready())
        if successful:
            self.assertTrue(g.successful(), (repr(g), g.value, g.exception))
            self.assertIsInstance(g.value, gevent.GreenletExit)
            self.assertIsNone(g.exception)
        else:
            self.assertFalse(g.successful(), (repr(g), g.value, g.exception))
            self.assertNotIsInstance(g.value, gevent.GreenletExit)
            self.assertIsNotNone(g.exception)

    def assertKilled(self, g, successful=True):
        self.__assertKilled(g, successful)
        gevent.sleep(0.01) # spin the loop to make sure it doesn't run.
        self.__assertKilled(g, successful)

    def __kill_greenlet(self, g, block, killall, exc=None):
        if exc is None:
            exc = gevent.GreenletExit
        if killall:
            killer = functools.partial(gevent.killall, [g],
                                       exception=exc, block=block)
        else:
            killer = functools.partial(g.kill, exception=exc, block=block)
        killer()
        if not block:
            # Must spin the loop to take effect (if it was scheduled)
            gevent.sleep(timing.SMALLEST_RELIABLE_DELAY)

        successful = exc is None or (isinstance(exc, type) and issubclass(exc, gevent.GreenletExit))
        self.assertKilled(g, successful)
        # kill second time must not hurt
        killer()
        self.assertKilled(g, successful)

    @staticmethod
    def _run_in_greenlet(result_collector):
        result_collector.append(1)

    def _start_greenlet(self, g):
        """
        Subclasses should override. This doesn't actually start a greenlet.
        """

    _after_kill_greenlet = _start_greenlet


    def _do_test(self, block, killall, exc=None):
        link_test = []
        result = []
        g = gevent.Greenlet(self._run_in_greenlet, result)
        g.link(link_test.append)

        self._start_greenlet(g)

        self.__kill_greenlet(g, block, killall, exc)

        self._after_kill_greenlet(g)

        self.assertFalse(result)
        self.assertEqual(link_test, [g])

    def test_block(self):
        self._do_test(block=True, killall=False)

    def test_non_block(self):
        self._do_test(block=False, killall=False)

    def test_block_killall(self):
        self._do_test(block=True, killall=True)

    def test_non_block_killal(self):
        self._do_test(block=False, killall=True)

    def test_non_type_exception(self):
        self._do_test(block=True, killall=False, exc=Exception())

    def test_non_type_exception_non_block(self):
        self._do_test(block=False, killall=False, exc=Exception())

    def test_non_type_exception_killall(self):
        self._do_test(block=True, killall=True, exc=Exception())

    def test_non_type_exception_killall_non_block(self):
        self._do_test(block=False, killall=True, exc=Exception())

    def test_non_exc_exception(self):
        self._do_test(block=True, killall=False, exc=42)

    def test_non_exc_exception_non_block(self):
        self._do_test(block=False, killall=False, exc=42)

    def test_non_exc_exception_killall(self):
        self._do_test(block=True, killall=True, exc=42)

    def test_non_exc_exception_killall_non_block(self):
        self._do_test(block=False, killall=True, exc=42)


class TestKillAfterStart(TestKill):

    def _start_greenlet(self, g):
        g.start()

class TestKillAfterStartLater(TestKill):

    def _start_greenlet(self, g):
        g.start_later(timing.LARGE_TICK)

class TestKillWhileRunning(TestKill):

    @staticmethod
    def _run_in_greenlet(result_collector):
        gevent.sleep(10)
        # The above should die with the GreenletExit exception,
        # so this should never run
        TestKill._run_in_greenlet(result_collector)

    def _after_kill_greenlet(self, g):
        TestKill._after_kill_greenlet(self, g)
        gevent.sleep(0.01)

class TestKillallRawGreenlet(greentest.TestCase):

    def test_killall_raw(self):
        g = gevent.spawn_raw(lambda: 1)
        gevent.killall([g])


class TestContextManager(greentest.TestCase):

    def test_simple(self):
        with gevent.spawn(gevent.sleep, timing.SMALL_TICK) as g:
            self.assert_greenlet_spawned(g)
        # It is completed after the suite
        self.assert_greenlet_finished(g)

    def test_wait_in_suite(self):
        with gevent.spawn(self._raise_exception) as g:
            with self.assertRaises(greentest.ExpectedException):
                g.get()
        self.assert_greenlet_finished(g)

    @staticmethod
    def _raise_exception():
        raise greentest.ExpectedException

    def test_greenlet_raises(self):
        with gevent.spawn(self._raise_exception) as g:
            pass

        self.assert_greenlet_finished(g)
        with self.assertRaises(greentest.ExpectedException):
            g.get()

    def test_join_raises(self):
        suite_ran = 0
        with self.assertRaises(ExpectedJoinError):
            with GreenletRaisesJoin.spawn(gevent.sleep, timing.SMALL_TICK) as g:
                self.assert_greenlet_spawned(g)
                suite_ran = 1

        self.assertTrue(suite_ran)
        self.assert_greenlet_finished(g)
        self.assertTrue(g.killed)

    def test_suite_body_raises(self, delay=None):
        greenlet_sleep = timing.SMALL_TICK if not delay else timing.LARGE_TICK
        with self.assertRaises(SuiteExpectedException):
            with GreenletRaisesJoin.spawn(gevent.sleep, greenlet_sleep) as g:
                self.assert_greenlet_spawned(g)
                if delay:
                    g.raise_on_join = False
                    gevent.sleep(delay)
                raise SuiteExpectedException

        self.assert_greenlet_finished(g)
        self.assertTrue(g.killed)
        if delay:
            self.assertTrue(g.joined)
        else:
            self.assertFalse(g.joined)
        self.assertFalse(g.successful())

        with self.assertRaises(SuiteExpectedException):
            g.get()

    def test_suite_body_raises_with_delay(self):
        self.test_suite_body_raises(delay=timing.SMALL_TICK)

class TestStart(greentest.TestCase):

    def test_start(self):
        g = gevent.spawn(gevent.sleep, timing.SMALL_TICK)
        self.assert_greenlet_spawned(g)

        g.start()
        self.assert_greenlet_started(g)

        g.join()
        self.assert_greenlet_finished(g)

        # cannot start again
        g.start()
        self.assert_greenlet_finished(g)


class TestRef(greentest.TestCase):

    def test_init(self):
        self.switch_expected = False
        # in python-dbg mode this will check that Greenlet() does not create any circular refs
        gevent.Greenlet()

    def test_kill_scheduled(self):
        gevent.spawn(gevent.sleep, timing.LARGE_TICK).kill()

    def test_kill_started(self):
        g = gevent.spawn(gevent.sleep, timing.LARGE_TICK)
        try:
            gevent.sleep(timing.SMALLEST_RELIABLE_DELAY)
        finally:
            g.kill()


@greentest.skipOnPurePython("Needs C extension")
class TestCExt(greentest.TestCase): # pragma: no cover (we only do coverage on pure-Python)

    def test_c_extension(self):
        self.assertEqual(greenlet.Greenlet.__module__,
                         'gevent._gevent_cgreenlet')
        self.assertEqual(greenlet.SpawnedLink.__module__,
                         'gevent._gevent_cgreenlet')

@greentest.skipWithCExtensions("Needs pure python")
class TestPure(greentest.TestCase):

    def test_pure(self):
        self.assertEqual(greenlet.Greenlet.__module__,
                         'gevent.greenlet')
        self.assertEqual(greenlet.SpawnedLink.__module__,
                         'gevent.greenlet')


X = object()

del AbstractGenericGetTestCase
del AbstractGenericWaitTestCase


if __name__ == '__main__':
    greentest.main()
