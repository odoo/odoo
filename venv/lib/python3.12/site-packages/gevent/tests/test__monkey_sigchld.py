import errno
import os
import sys

import gevent
import gevent.monkey
gevent.monkey.patch_all()

pid = None
awaiting_child = []


def handle_sigchld(*_args):
    # Make sure we can do a blocking operation
    gevent.sleep()
    # Signal completion
    awaiting_child.pop()
    # Raise an ignored error
    raise TypeError("This should be ignored but printed")

# Try to produce output compatible with unittest output so
# our status parsing functions work.

import signal
if hasattr(signal, 'SIGCHLD'):
    # In Python 3.8.0 final, on both Travis CI/Linux and locally
    # on macOS, the *child* process started crashing on exit with a memory
    # error:
    #
    # Debug memory block at address p=0x7fcf5d6b5000: API ''
    #     6508921152173528397 bytes originally requested
    #     The 7 pad bytes at p-7 are not all FORBIDDENBYTE (0xfd):
    #
    # When PYTHONDEVMODE is set. This happens even if we just simply fork
    # the child process and don't have gevent even /imported/ in the most
    # minimal test case. It's not clear what caused that.
    if sys.version_info[:2] >= (3, 8) and os.environ.get("PYTHONDEVMODE"):
        print("Ran 1 tests in 0.0s (skipped=1)")
        sys.exit(0)


    assert signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL
    signal.signal(signal.SIGCHLD, handle_sigchld)
    handler = signal.getsignal(signal.SIGCHLD)
    assert signal.getsignal(signal.SIGCHLD) is handle_sigchld, handler

    if hasattr(os, 'forkpty'):
        def forkpty():
            # For printing in errors
            return os.forkpty()[0]
        funcs = (os.fork, forkpty)
    else:
        funcs = (os.fork,)

    for func in funcs:
        awaiting_child = [True]
        pid = func()
        if not pid:
            # child
            gevent.sleep(0.3)
            sys.exit(0)
        else:
            timeout = gevent.Timeout(1)
            try:
                while awaiting_child:
                    gevent.sleep(0.01)
                # We should now be able to waitpid() for an arbitrary child
                wpid, status = os.waitpid(-1, os.WNOHANG)
                if wpid != pid:
                    raise AssertionError("Failed to wait on a child pid forked with a function",
                                         wpid, pid, func)

                # And a second call should raise ECHILD
                try:
                    wpid, status = os.waitpid(-1, os.WNOHANG)
                    raise AssertionError("Should not be able to wait again")
                except OSError as e:
                    assert e.errno == errno.ECHILD
            except gevent.Timeout as t:
                if timeout is not t:
                    raise
                raise AssertionError("Failed to wait using", func)
            finally:
                timeout.close()
    print("Ran 1 tests in 0.0s")
    sys.exit(0)
else:
    print("No SIGCHLD, not testing")
    print("Ran 1 tests in 0.0s (skipped=1)")
