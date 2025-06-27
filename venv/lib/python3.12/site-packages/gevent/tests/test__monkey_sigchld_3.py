# Mimics what gunicorn workers do *if* the arbiter is also monkey-patched:
# After forking from the master monkey-patched process, the child
# resets signal handlers to SIG_DFL. If we then fork and watch *again*,
# we shouldn't hang. (Note that we carefully handle this so as not to break
# os.popen)
from __future__ import print_function
# Patch in the parent process.
import gevent.monkey
gevent.monkey.patch_all()

from gevent import get_hub

import os
import sys

import signal
import subprocess

def _waitpid(p):
    try:
        _, stat = os.waitpid(p, 0)
    except OSError:
        # Interrupted system call
        _, stat = os.waitpid(p, 0)
    assert stat == 0, stat

if hasattr(signal, 'SIGCHLD'):
    if sys.version_info[:2] >= (3, 8) and os.environ.get("PYTHONDEVMODE"):
        # See test__monkey_sigchld.py
        print("Ran 1 tests in 0.0s (skipped=1)")
        sys.exit(0)

    # Do what subprocess does and make sure we have the watcher
    # in the parent
    get_hub().loop.install_sigchld()


    pid = os.fork()

    if pid: # parent
        _waitpid(pid)
    else:
        # Child resets.
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)

        # Go through subprocess because we expect it to automatically
        # set up the waiting for us.
        # not on Py2 pylint:disable=consider-using-with
        popen = subprocess.Popen([sys.executable, '-c', 'import sys'],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        popen.stderr.read()
        popen.stdout.read()
        popen.wait() # This hangs if it doesn't.
        popen.stderr.close()
        popen.stdout.close()
        sys.exit(0)
else:
    print("No SIGCHLD, not testing")
    print("Ran 1 tests in 0.0s (skipped=1)")
