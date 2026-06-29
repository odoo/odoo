'''Test for GitHub issues 461 and 471.

When moving to Python 3, handling of KeyboardInterrupt exceptions caused
by a Ctrl-C raised an exception while printing the traceback for a
greenlet preventing the process from exiting. This test tests for proper
handling of KeyboardInterrupt.
'''

import sys

if sys.argv[1:] == ['subprocess']: # pragma: no cover
    import gevent

    def task():
        sys.stdout.write('ready\n')
        sys.stdout.flush()
        gevent.sleep(30)

    try:
        gevent.spawn(task).get()
    except KeyboardInterrupt:
        pass

    sys.exit(0)

else:
    import signal
    from subprocess import Popen, PIPE
    import time

    import unittest
    import gevent.testing as greentest
    from gevent.testing.sysinfo import CFFI_BACKEND
    from gevent.testing.sysinfo import RUN_COVERAGE
    from gevent.testing.sysinfo import WIN
    from gevent.testing.sysinfo import PYPY3

    class Test(unittest.TestCase):

        @unittest.skipIf(
            (CFFI_BACKEND and RUN_COVERAGE) or (PYPY3 and WIN),
            "Interferes with the timing; times out waiting for the child")
        def test_hang(self):
            # XXX: Why does PyPy3 on Win fail to kill the child? (This was before we switched
            # to pypy3w; perhaps that makes a difference?)
            if WIN:
                from subprocess import CREATE_NEW_PROCESS_GROUP
                kwargs = {'creationflags': CREATE_NEW_PROCESS_GROUP}
            else:
                kwargs = {}
            # (not on Py2) pylint:disable=consider-using-with
            p = Popen([sys.executable, __file__, 'subprocess'], stdout=PIPE, **kwargs)
            line = p.stdout.readline()
            if not isinstance(line, str):
                line = line.decode('ascii')
            # Windows needs the \n in the string to write (because of buffering), but
            # because of newline handling it doesn't make it through the read; whereas
            # it does on other platforms. Universal newlines is broken on Py3, so the best
            # thing to do is to strip it
            line = line.strip()
            self.assertEqual(line, 'ready')
            # On Windows, we have to send the CTRL_BREAK_EVENT (which seems to terminate the process); SIGINT triggers
            # "ValueError: Unsupported signal: 2". The CTRL_C_EVENT is ignored on Python 3 (but not Python 2).
            # So this test doesn't test much on Windows.
            signal_to_send = signal.SIGINT if not WIN else getattr(signal, 'CTRL_BREAK_EVENT')
            p.send_signal(signal_to_send)
            # Wait a few seconds for child process to die. Sometimes signal delivery is delayed
            # or even swallowed by Python, so send the signal a few more times if necessary
            wait_seconds = 25.0
            now = time.time()
            midtime = now + (wait_seconds / 2.0)
            endtime = time.time() + wait_seconds
            while time.time() < endtime:
                if p.poll() is not None:
                    break
                if time.time() > midtime:
                    p.send_signal(signal_to_send)
                    midtime = endtime + 1 # only once
                time.sleep(0.1)
            else:
                # Kill unresponsive child and exit with error 1
                p.terminate()
                p.wait()
                raise AssertionError("Failed to wait for child")

            # If we get here, it's because we caused the process to exit; it
            # didn't hang. Under Windows, however, we have to use CTRL_BREAK_EVENT,
            # which has an arbitrary returncode depending on versions (so does CTRL_C_EVENT
            # on Python 2). We still
            # count this as success.
            self.assertEqual(p.returncode if not WIN else 0, 0)
            p.stdout.close()

    if __name__ == '__main__':
        greentest.main()
