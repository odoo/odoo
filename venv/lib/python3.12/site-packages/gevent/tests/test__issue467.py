import gevent
from gevent import testing as greentest

#import socket # on windows

# iwait should not raise `LoopExit: This operation would block forever`
# or `AssertionError: Invalid switch into ...`
# if the caller of iwait causes greenlets to switch in between
# return values


def worker(i):
    # Have one of them raise an exception to test that case
    if i == 2:
        raise ValueError(i)
    return i

class Test(greentest.TestCase):
    def test(self):
        finished = 0
        # Wait on a group that includes one that will already be
        # done, plus some that will finish as we watch
        done_worker = gevent.spawn(worker, "done")
        gevent.joinall((done_worker,))

        workers = [gevent.spawn(worker, i) for i in range(3)]
        workers.append(done_worker)
        for _ in gevent.iwait(workers):
            finished += 1
            # Simulate doing something that causes greenlets to switch;
            # a non-zero timeout is crucial
            try:
                gevent.sleep(0.01)
            except ValueError as ex:
                self.assertEqual(ex.args[0], 2)

        self.assertEqual(finished, 4)

if __name__ == '__main__':
    greentest.main()
