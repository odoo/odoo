import sys
import os
import glob

import atexit
# subprocess: include in subprocess tests

from gevent.testing import util
from gevent.testing import sysinfo
from gevent.testing.support import is_resource_enabled

TIMEOUT = 120

# XXX: Generalize this so other packages can use it.


def get_absolute_pythonpath():
    paths = [os.path.abspath(p) for p in os.environ.get('PYTHONPATH', '').split(os.pathsep)]
    return os.pathsep.join(paths)


def TESTRUNNER(tests=None):
    if not is_resource_enabled('gevent_monkey'):
        util.log('WARNING: Testing monkey-patched stdlib has been disabled',
                 color="suboptimal-behaviour")
        return

    try:
        test_dir, version_test_dir = util.find_stdlib_tests()
    except util.NoSetupPyFound as e:
        util.log("WARNING: No setup.py and src/greentest found: %r", e,
                 color="suboptimal-behaviour")
        return

    if not os.path.exists(test_dir):
        util.log('WARNING: No test directory found at %s', test_dir,
                 color="suboptimal-behaviour")
        return

    # pylint:disable=unspecified-encoding
    with open(os.path.join(test_dir, 'version')) as f:
        preferred_version = f.read().strip()

    running_version = sysinfo.get_python_version()
    if preferred_version != running_version:
        util.log('WARNING: The tests in %s/ are from version %s and your Python is %s',
                 test_dir, preferred_version, running_version,
                 color="suboptimal-behaviour")

    version_tests = glob.glob('%s/test_*.py' % version_test_dir)
    version_tests = sorted(version_tests)
    if not tests:
        tests = glob.glob('%s/test_*.py' % test_dir)
        tests = sorted(tests)

    PYTHONPATH = (os.getcwd() + os.pathsep + get_absolute_pythonpath()).rstrip(':')

    tests = sorted(set(os.path.basename(x) for x in tests))
    version_tests = sorted(set(os.path.basename(x) for x in version_tests))

    util.log("Discovered %d tests in %s", len(tests), test_dir)
    util.log("Discovered %d version-specific tests in %s", len(version_tests), version_test_dir)

    options = {
        'cwd': test_dir,
        'timeout': TIMEOUT,
        'setenv': {
            'PYTHONPATH': PYTHONPATH,
            # debug produces resource tracking warnings for the
            # CFFI backends. On Python 2, many of the stdlib tests
            # rely on refcounting to close sockets so they produce
            # lots of noise. Python 3 is not completely immune;
            # test_ftplib.py tends to produce warnings---and the Python 3
            # test framework turns those into test failures!
            'GEVENT_DEBUG': 'error',
        }
    }

    if tests and not sys.platform.startswith("win"):
        atexit.register(os.system, 'rm -f */@test*')

    basic_args = [sys.executable, '-u', '-W', 'ignore', '-m', 'gevent.testing.monkey_test']
    for filename in tests:
        if filename in version_tests:
            util.log("Overriding %s from %s with file from %s", filename, test_dir, version_test_dir)
            continue
        yield basic_args + [filename], options.copy()

    options['cwd'] = version_test_dir
    for filename in version_tests:
        yield basic_args + [filename], options.copy()


def main():
    from gevent.testing import testrunner
    discovered_tests = TESTRUNNER(sys.argv[1:])
    discovered_tests = list(discovered_tests)
    return testrunner.Runner(discovered_tests, quiet=None)()


if __name__ == '__main__':
    main()
