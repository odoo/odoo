import sys
import os


test_filename = sys.argv[1]
del sys.argv[1]

if test_filename == 'test_urllib2_localnet.py' and os.environ.get('APPVEYOR'):
    os.environ['GEVENT_DEBUG'] = 'TRACE'

print('Running with patch_all(): %s' % (test_filename,))

from gevent import monkey
# Only test the default set of patch arguments.
monkey.patch_all()

from .sysinfo import PY3
from .patched_tests_setup import disable_tests_in_source
from . import support
from . import resources
from . import SkipTest
from . import util



# This uses the internal built-in function ``_thread._count()``,
# which we don't/can't monkey-patch, so it returns inaccurate information.
def threading_setup():
    if PY3:
        return (1, ())
    return (1,)
# This then tries to wait for that value to return to its original value;
# but if we started worker threads that can never happen.
def threading_cleanup(*_args):
    return
support.threading_setup = threading_setup
support.threading_cleanup = threading_cleanup


# On all versions of Python 3.6+, this also uses ``_thread._count()``,
# meaning it suffers from inaccuracies,
# and test_socket.py constantly fails with an extra thread
# on some random test. We disable it entirely.
# XXX: Figure out how to make a *definition* in ./support.py actually
# override the original in test.support, without having to
# manually set it
#
import contextlib
@contextlib.contextmanager
def wait_threads_exit(timeout=None): # pylint:disable=unused-argument
    yield
support.wait_threads_exit = wait_threads_exit

# On Python 3.11, they changed the way that they deal with this,
# meaning that this method no longer works. (Actually, it's not
# clear that any of our patches to `support` are doing anything on
# Python 3 at all? They certainly aren't on 3.11). This was a good
# thing As it led to adding the timeout value for the threadpool
# idle threads. But...the default of 5s meant that many tests in
# test_socket were each taking at least 5s to run, leading to the
# whole thing exceeding the allowed test timeout. We could set the
# GEVENT_THREADPOOL_IDLE_TASK_TIMEOUT env variable to a smaller
# value, and although that might stress the system nicely, it's
# not indicative of what end users see. And it's still hard to get
# a correct value.
#
# So try harder to make sure our patches apply.
#
# If this fails, symptoms are very long running tests that can be resolved
# by setting that TASK_TIMEOUT value small, and/or setting GEVENT_RESOLVER=block.
# Also, some number of warnings about dangling threads, or failures
# from wait_threads_exit
try:
    from test import support as ts
except ImportError:
    pass
else:
    ts.threading_setup = threading_setup
    ts.threading_cleanup = threading_cleanup
    ts.wait_threads_exit = wait_threads_exit

try:
    from test.support import threading_helper
except ImportError:
    pass
else:
    threading_helper.wait_threads_exit = wait_threads_exit
    threading_helper.threading_setup = threading_setup
    threading_helper.threading_cleanup = threading_cleanup

# So we don't have to patch test_threading to use our
# version of lock_tests, we patch
from gevent.tests import lock_tests
try:
    import test.lock_tests
except ImportError:
    pass
else:
    test.lock_tests = lock_tests
    sys.modules['tests.lock_tests'] = lock_tests

# Configure allowed resources
resources.setup_resources()

if not os.path.exists(test_filename) and os.sep not in test_filename:
    # A simple filename, given without a path, that doesn't exist.
    # So we change to the appropriate directory, if we can find it.
    # This happens when copy-pasting the output of the testrunner
    for d in util.find_stdlib_tests():
        if os.path.exists(os.path.join(d, test_filename)):
            os.chdir(d)
            break

__file__ = os.path.join(os.getcwd(), test_filename)

test_name = os.path.splitext(test_filename)[0]

# It's important that the `module_source` be a native
# string. Passing unicode to `compile` on Python 2 can
# do bad things: it conflicts with a 'coding:' directive,
# and it can cause some TypeError with string literals
# We do use with; just not on the same line!
if sys.version_info[0] >= 3:
    module_file = open(test_filename, encoding='utf-8') # pylint:disable=consider-using-with
else:
    module_file = open(test_filename) # pylint:disable=consider-using-with,unspecified-encoding
with module_file:
    module_source = module_file.read()
module_source = disable_tests_in_source(module_source, test_name)

# We write the module source to a file so that tracebacks
# show correctly, since disabling the tests changes line
# numbers. However, note that __file__ must still point to the
# real location so that data files can be found.
# See https://github.com/gevent/gevent/issues/1306
import tempfile
temp_handle, temp_path = tempfile.mkstemp(prefix=test_name, suffix='.py', text=True)
os.write(temp_handle,
         module_source.encode('utf-8') if not isinstance(module_source, bytes) else module_source)
os.close(temp_handle)
try:
    module_code = compile(module_source,
                          temp_path,
                          'exec',
                          dont_inherit=True)
    exec(module_code, globals())
except SkipTest as e:
    # Some tests can raise test.support.ResourceDenied
    # in their main method before the testrunner takes over.
    # That's a kind of SkipTest. we can't get a true skip count because it
    # hasn't run, though.
    print(e)
    # Match the regular unittest output, including ending with skipped
    print("Ran 0 tests in 0.0s")
    print('OK (skipped=0)')
finally:
    try:
        os.remove(temp_path)
    except OSError:
        pass
