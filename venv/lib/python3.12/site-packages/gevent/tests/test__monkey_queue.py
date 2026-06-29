# Some simple queue module tests, plus some failure conditions
# to ensure the Queue locks remain stable.
from gevent import monkey
monkey.patch_all()

from gevent import queue as Queue
import threading
import time
import unittest


QUEUE_SIZE = 5

# A thread to run a function that unclogs a blocked Queue.
class _TriggerThread(threading.Thread):
    def __init__(self, fn, args):
        self.fn = fn
        self.args = args
        #self.startedEvent = threading.Event()
        from gevent.event import Event
        self.startedEvent = Event()
        threading.Thread.__init__(self)

    def run(self):
        # The sleep isn't necessary, but is intended to give the blocking
        # function in the main thread a chance at actually blocking before
        # we unclog it.  But if the sleep is longer than the timeout-based
        # tests wait in their blocking functions, those tests will fail.
        # So we give them much longer timeout values compared to the
        # sleep here (I aimed at 10 seconds for blocking functions --
        # they should never actually wait that long - they should make
        # progress as soon as we call self.fn()).
        time.sleep(0.01)
        self.startedEvent.set()
        self.fn(*self.args)


# Execute a function that blocks, and in a separate thread, a function that
# triggers the release.  Returns the result of the blocking function.  Caution:
# block_func must guarantee to block until trigger_func is called, and
# trigger_func must guarantee to change queue state so that block_func can make
# enough progress to return.  In particular, a block_func that just raises an
# exception regardless of whether trigger_func is called will lead to
# timing-dependent sporadic failures, and one of those went rarely seen but
# undiagnosed for years.  Now block_func must be unexceptional.  If block_func
# is supposed to raise an exception, call do_exceptional_blocking_test()
# instead.

class BlockingTestMixin(object):

    def do_blocking_test(self, block_func, block_args, trigger_func, trigger_args):
        self.t = _TriggerThread(trigger_func, trigger_args)
        self.t.start()
        self.result = block_func(*block_args)
        # If block_func returned before our thread made the call, we failed!
        if not self.t.startedEvent.isSet():
            self.fail("blocking function '%r' appeared not to block" %
                      block_func)
        self.t.join(10) # make sure the thread terminates
        if self.t.is_alive():
            self.fail("trigger function '%r' appeared to not return" %
                      trigger_func)
        return self.result

    # Call this instead if block_func is supposed to raise an exception.
    def do_exceptional_blocking_test(self, block_func, block_args, trigger_func,
                                     trigger_args, expected_exception_class):
        self.t = _TriggerThread(trigger_func, trigger_args)
        self.t.start()
        try:
            with self.assertRaises(expected_exception_class):
                block_func(*block_args)
        finally:
            self.t.join(10) # make sure the thread terminates
            if self.t.is_alive():
                self.fail("trigger function '%r' appeared to not return" %
                          trigger_func)
            if not self.t.startedEvent.isSet():
                self.fail("trigger thread ended but event never set")


class BaseQueueTest(unittest.TestCase, BlockingTestMixin):
    type2test = Queue.Queue

    def setUp(self):
        self.cum = 0
        self.cumlock = threading.Lock()

    def simple_queue_test(self, q):
        if not q.empty():
            raise RuntimeError("Call this function with an empty queue")
        # I guess we better check things actually queue correctly a little :)
        q.put(111)
        q.put(333)
        q.put(222)
        q.put(444)
        target_first_items = dict(
            Queue=111,
            LifoQueue=444,
            PriorityQueue=111)
        actual_first_item = (q.peek(), q.get())
        self.assertEqual(actual_first_item,
                         (target_first_items[q.__class__.__name__],
                          target_first_items[q.__class__.__name__]),
                         "q.peek() and q.get() are not equal!")
        target_order = dict(Queue=[333, 222, 444],
                            LifoQueue=[222, 333, 111],
                            PriorityQueue=[222, 333, 444])
        actual_order = [q.get(), q.get(), q.get()]
        self.assertEqual(actual_order, target_order[q.__class__.__name__],
                         "Didn't seem to queue the correct data!")
        for i in range(QUEUE_SIZE-1):
            q.put(i)
            self.assertFalse(q.empty(), "Queue should not be empty")
        self.assertFalse(q.full(), "Queue should not be full")
        q.put(999)
        self.assertTrue(q.full(), "Queue should be full")
        try:
            q.put(888, block=0)
            self.fail("Didn't appear to block with a full queue")
        except Queue.Full:
            pass
        try:
            q.put(888, timeout=0.01)
            self.fail("Didn't appear to time-out with a full queue")
        except Queue.Full:
            pass
        self.assertEqual(q.qsize(), QUEUE_SIZE)
        # Test a blocking put
        self.do_blocking_test(q.put, (888,), q.get, ())
        self.do_blocking_test(q.put, (888, True, 10), q.get, ())
        # Empty it
        for i in range(QUEUE_SIZE):
            q.get()
        self.assertTrue(q.empty(), "Queue should be empty")
        try:
            q.get(block=0)
            self.fail("Didn't appear to block with an empty queue")
        except Queue.Empty:
            pass
        try:
            q.get(timeout=0.01)
            self.fail("Didn't appear to time-out with an empty queue")
        except Queue.Empty:
            pass
        # Test a blocking get
        self.do_blocking_test(q.get, (), q.put, ('empty',))
        self.do_blocking_test(q.get, (True, 10), q.put, ('empty',))

    def worker(self, q):
        while True:
            x = q.get()
            if x is None:
                q.task_done()
                return
            #with self.cumlock:
            self.cum += x
            q.task_done()

    def queue_join_test(self, q):
        self.cum = 0
        for i in (0, 1):
            threading.Thread(target=self.worker, args=(q,)).start()
        for i in range(100):
            q.put(i)
        q.join()
        self.assertEqual(self.cum, sum(range(100)),
                         "q.join() did not block until all tasks were done")
        for i in (0, 1):
            q.put(None)         # instruct the threads to close
        q.join()                # verify that you can join twice

    def test_queue_task_done(self):
        # Test to make sure a queue task completed successfully.
        q = Queue.JoinableQueue() # self.type2test()
        # XXX the same test in subclasses
        try:
            q.task_done()
        except ValueError:
            pass
        else:
            self.fail("Did not detect task count going negative")

    def test_queue_join(self):
        # Test that a queue join()s successfully, and before anything else
        # (done twice for insurance).
        q = Queue.JoinableQueue() # self.type2test()
        # XXX the same test in subclass
        self.queue_join_test(q)
        self.queue_join_test(q)
        try:
            q.task_done()
        except ValueError:
            pass
        else:
            self.fail("Did not detect task count going negative")

    def test_queue_task_done_with_items(self):
        # Passing items to the constructor allows for as
        # many task_done calls. Joining before all the task done
        # are called returns false
        # XXX the same test in subclass
        l = [1, 2, 3]
        q = Queue.JoinableQueue(items=l)
        for i in l:
            self.assertFalse(q.join(timeout=0.001))
            self.assertEqual(i, q.get())
            q.task_done()

        try:
            q.task_done()
        except ValueError:
            pass
        else:
            self.fail("Did not detect task count going negative")
        self.assertTrue(q.join(timeout=0.001))

    def test_simple_queue(self):
        # Do it a couple of times on the same queue.
        # Done twice to make sure works with same instance reused.
        q = self.type2test(QUEUE_SIZE)
        self.simple_queue_test(q)
        self.simple_queue_test(q)

class LifoQueueTest(BaseQueueTest):
    type2test = Queue.LifoQueue

class PriorityQueueTest(BaseQueueTest):
    type2test = Queue.PriorityQueue

    def test__init(self):
        item1 = (2, 'b')
        item2 = (1, 'a')
        q = self.type2test(items=[item1, item2])
        self.assertTupleEqual(item2, q.get_nowait())
        self.assertTupleEqual(item1, q.get_nowait())


# A Queue subclass that can provoke failure at a moment's notice :)
class FailingQueueException(Exception):
    pass

class FailingQueue(Queue.Queue):
    def __init__(self, *args):
        self.fail_next_put = False
        self.fail_next_get = False
        Queue.Queue.__init__(self, *args)
    def _put(self, item):
        if self.fail_next_put:
            self.fail_next_put = False
            raise FailingQueueException("You Lose")
        return Queue.Queue._put(self, item)
    def _get(self):
        if self.fail_next_get:
            self.fail_next_get = False
            raise FailingQueueException("You Lose")
        return Queue.Queue._get(self)

class FailingQueueTest(unittest.TestCase, BlockingTestMixin):

    def failing_queue_test(self, q):
        if not q.empty():
            raise RuntimeError("Call this function with an empty queue")
        for i in range(QUEUE_SIZE-1):
            q.put(i)
        # Test a failing non-blocking put.
        q.fail_next_put = True
        with self.assertRaises(FailingQueueException):
            q.put("oops", block=0)

        q.fail_next_put = True
        with self.assertRaises(FailingQueueException):
            q.put("oops", timeout=0.1)
        q.put(999)
        self.assertTrue(q.full(), "Queue should be full")
        # Test a failing blocking put
        q.fail_next_put = True
        with self.assertRaises(FailingQueueException):
            self.do_blocking_test(q.put, (888,), q.get, ())

        # Check the Queue isn't damaged.
        # put failed, but get succeeded - re-add
        q.put(999)
        # Test a failing timeout put
        q.fail_next_put = True
        self.do_exceptional_blocking_test(q.put, (888, True, 10), q.get, (),
                                          FailingQueueException)
        # Check the Queue isn't damaged.
        # put failed, but get succeeded - re-add
        q.put(999)
        self.assertTrue(q.full(), "Queue should be full")
        q.get()
        self.assertFalse(q.full(), "Queue should not be full")
        q.put(999)
        self.assertTrue(q.full(), "Queue should be full")
        # Test a blocking put
        self.do_blocking_test(q.put, (888,), q.get, ())
        # Empty it
        for i in range(QUEUE_SIZE):
            q.get()
        self.assertTrue(q.empty(), "Queue should be empty")
        q.put("first")
        q.fail_next_get = True
        with self.assertRaises(FailingQueueException):
            q.get()

        self.assertFalse(q.empty(), "Queue should not be empty")
        q.fail_next_get = True
        with self.assertRaises(FailingQueueException):
            q.get(timeout=0.1)
        self.assertFalse(q.empty(), "Queue should not be empty")
        q.get()
        self.assertTrue(q.empty(), "Queue should be empty")
        q.fail_next_get = True
        self.do_exceptional_blocking_test(q.get, (), q.put, ('empty',),
                                          FailingQueueException)
        # put succeeded, but get failed.
        self.assertFalse(q.empty(), "Queue should not be empty")
        q.get()
        self.assertTrue(q.empty(), "Queue should be empty")

    def test_failing_queue(self):
        # Test to make sure a queue is functioning correctly.
        # Done twice to the same instance.
        q = FailingQueue(QUEUE_SIZE)
        self.failing_queue_test(q)
        self.failing_queue_test(q)


if __name__ == "__main__":
    unittest.main()
