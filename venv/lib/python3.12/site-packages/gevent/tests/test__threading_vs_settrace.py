from __future__ import print_function
import sys
import subprocess
import unittest
from gevent.thread import allocate_lock
import gevent.testing as greentest

script = """
from gevent import monkey
monkey.patch_all() # pragma: testrunner-no-monkey-combine
import sys, os, threading, time


# A deadlock-killer, to prevent the
# testsuite to hang forever
def killer():
    time.sleep(0.2)
    sys.stdout.write('..program blocked; aborting!')
    sys.stdout.flush()
    os._exit(2)
t = threading.Thread(target=killer)
t.daemon = True
t.start()


def trace(frame, event, arg):
    if threading is not None:
        threading.current_thread()
    return trace


def doit():
    sys.stdout.write("..thread started..")


def test1():
    t = threading.Thread(target=doit)
    t.start()
    t.join()
    sys.settrace(None)

sys.settrace(trace)
if len(sys.argv) > 1:
    test1()

sys.stdout.write("..finishing..")
"""


class TestTrace(unittest.TestCase):
    @greentest.skipOnPurePython("Locks can be traced in Pure Python")
    def test_untraceable_lock(self):
        # Untraceable locks were part of the solution to https://bugs.python.org/issue1733757
        # which details a deadlock that could happen if a trace function invoked
        # threading.currentThread at shutdown time---the cleanup lock would be held
        # by the VM, and calling currentThread would try to acquire it again. The interpreter
        # changed in 2.6 to use the `with` statement (https://hg.python.org/cpython/rev/76f577a9ec03/),
        # which apparently doesn't trace in quite the same way.
        if hasattr(sys, 'gettrace'):
            old = sys.gettrace()
        else:
            old = None

        lst = []
        try:
            def trace(frame, ev, _arg):
                lst.append((frame.f_code.co_filename, frame.f_lineno, ev))
                print("TRACE: %s:%s %s" % lst[-1])
                return trace

            with allocate_lock():
                sys.settrace(trace)
        finally:
            sys.settrace(old)

        self.assertEqual(lst, [], "trace not empty")

    @greentest.skipOnPurePython("Locks can be traced in Pure Python")
    def test_untraceable_lock_uses_different_lock(self):
        if hasattr(sys, 'gettrace'):
            old = sys.gettrace()
        else:
            old = None

        lst = []
        # we should be able to use unrelated locks from within the trace function
        l = allocate_lock()
        try:
            def trace(frame, ev, _arg):
                with l:
                    lst.append((frame.f_code.co_filename, frame.f_lineno, ev))
                # print("TRACE: %s:%s %s" % lst[-1])
                return trace

            l2 = allocate_lock()
            sys.settrace(trace)
            # Separate functions, not the C-implemented `with` so the trace
            # function gets a crack at them
            l2.acquire()
            l2.release()
        finally:
            sys.settrace(old)

        # Have an assert so that we know if we miscompile
        self.assertTrue(lst, "should not compile on pypy")

    @greentest.skipOnPurePython("Locks can be traced in Pure Python")
    def test_untraceable_lock_uses_same_lock(self):
        from gevent.hub import LoopExit
        if hasattr(sys, 'gettrace'):
            old = sys.gettrace()
        else:
            old = None

        lst = []
        e = None
        # we should not be able to use the same lock from within the trace function
        # because it's over acquired but instead of deadlocking it raises an exception
        l = allocate_lock()
        try:
            def trace(frame, ev, _arg):
                with l:
                    lst.append((frame.f_code.co_filename, frame.f_lineno, ev))
                return trace

            sys.settrace(trace)
            # Separate functions, not the C-implemented `with` so the trace
            # function gets a crack at them
            l.acquire()
        except LoopExit as ex:
            e = ex
        finally:
            sys.settrace(old)

        # Have an assert so that we know if we miscompile
        self.assertTrue(lst, "should not compile on pypy")
        self.assertTrue(isinstance(e, LoopExit))

    def run_script(self, more_args=()):
        if (
                greentest.PYPY3
                and greentest.RUNNING_ON_APPVEYOR
                and sys.version_info[:2] == (3, 7)
        ):
            # Somehow launching the subprocess fails with exit code 1, and
            # produces no output. It's not clear why.
            self.skipTest("Known to hang on AppVeyor")
        args = [sys.executable, "-u", "-c", script]
        args.extend(more_args)
        rc = subprocess.call(args)
        self.assertNotEqual(rc, 2, "interpreter was blocked")
        self.assertEqual(rc, 0, "Unexpected error")

    def test_finalize_with_trace(self):
        self.run_script()

    def test_bootstrap_inner_with_trace(self):
        self.run_script(["1"])


if __name__ == "__main__":
    greentest.main()
