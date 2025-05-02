# Mimics what gunicorn workers do: monkey patch in the child process
# and try to reset signal handlers to SIG_DFL.
# NOTE: This breaks again when gevent.subprocess is used, or any child
# watcher.
import os
import sys

import signal


def handle(*_args):
    if not pid:
        # We only do this is the child so our
        # parent's waitpid can get the status.
        # This is the opposite of gunicorn.
        os.waitpid(-1, os.WNOHANG)
# The signal watcher must be installed *before* monkey patching
if hasattr(signal, 'SIGCHLD'):
    if sys.version_info[:2] >= (3, 8) and os.environ.get("PYTHONDEVMODE"):
        # See test__monkey_sigchld.py
        print("Ran 1 tests in 0.0s (skipped=1)")
        sys.exit(0)

    # On Python 2, the signal handler breaks the platform
    # module, because it uses os.popen. pkg_resources uses the platform
    # module.
    # Cache that info.
    import platform
    platform.uname()
    signal.signal(signal.SIGCHLD, handle)

    pid = os.fork()

    if pid: # parent
        try:
            _, stat = os.waitpid(pid, 0)
        except OSError:
            # Interrupted system call
            _, stat = os.waitpid(pid, 0)
        assert stat == 0, stat
    else:
        # Under Python 2, os.popen() directly uses the popen call, and
        # popen's file uses the pclose() system call to
        # wait for the child. If it's already waited on,
        # it raises the same exception.
        # Python 3 uses the subprocess module directly which doesn't
        # have this problem.
        import gevent.monkey
        gevent.monkey.patch_all()
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        f = os.popen('true')
        f.close()

        sys.exit(0)
else:
    print("No SIGCHLD, not testing")
