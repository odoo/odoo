#!/usr/bin/env python
from __future__ import print_function, absolute_import, division

import re
import sys
import os
import glob
import operator
import traceback
import importlib

from contextlib import contextmanager
from datetime import timedelta
from multiprocessing.pool import ThreadPool
from multiprocessing import cpu_count

from gevent._util import Lazy

from . import util
from .resources import parse_resources
from .resources import setup_resources
from .resources import unparse_resources
from .sysinfo import RUNNING_ON_CI
from .sysinfo import PYPY
from .sysinfo import PY2
from .sysinfo import RESOLVER_ARES
from .sysinfo import RUN_LEAKCHECKS
from .sysinfo import OSX
from . import six
from . import travis

# Import this while we're probably single-threaded/single-processed
# to try to avoid issues with PyPy 5.10.
# See https://bitbucket.org/pypy/pypy/issues/2769/systemerror-unexpected-internal-exception
try:
    __import__('_testcapi')
except (ImportError, OSError, IOError):
    # This can raise a wide variety of errors
    pass

TIMEOUT = 100 # seconds
AVAIL_NWORKERS = cpu_count() - 1
DEFAULT_NWORKERS = int(os.environ.get('NWORKERS') or max(AVAIL_NWORKERS, 4))
if DEFAULT_NWORKERS > 15:
    DEFAULT_NWORKERS = 10


if RUN_LEAKCHECKS:
    # Capturing the stats takes time, and we run each
    # test at least twice
    TIMEOUT = 200

DEFAULT_RUN_OPTIONS = {
    'timeout': TIMEOUT
}


if RUNNING_ON_CI:
    # Too many and we get spurious timeouts
    DEFAULT_NWORKERS = 4 if not OSX else 2


def _package_relative_filename(filename, package):
    if not os.path.isfile(filename) and package:
        # Ok, try to locate it as a module in the package
        package_dir = _dir_from_package_name(package)
        return os.path.join(package_dir, filename)
    return filename

def _dir_from_package_name(package):
    package_mod = importlib.import_module(package)
    package_dir = os.path.dirname(package_mod.__file__)
    return package_dir


class ResultCollector(object):

    def __init__(self):
        self.total = 0
        self.failed = {}
        self.passed = {}
        self.total_cases = 0
        self.total_skipped = 0
        # Every RunResult reported: failed, passed, rerun
        self._all_results = []
        self.reran = {}

    def __iadd__(self, result):
        self._all_results.append(result)

        if not result:
            self.failed[result.name] = result #[cmd, kwargs]
        else:
            self.passed[result.name] = True
        self.total_cases += result.run_count
        self.total_skipped += result.skipped_count
        return self

    def __ilshift__(self, result):
        """
        collector <<= result

        Stores the result, but does not count it towards
        the number of cases run, skipped, passed or failed.
        """
        self._all_results.append(result)
        self.reran[result.name] = result
        return self

    @property
    def longest_running_tests(self):
        """
        A new list of RunResult objects, sorted from longest running
        to shortest running.
        """
        return sorted(self._all_results,
                      key=operator.attrgetter('run_duration'),
                      reverse=True)


class FailFast(Exception):
    pass

class Runner(object):

    TIME_WAIT_REAP = 0.1
    TIME_WAIT_SPAWN = 0.05

    def __init__(self,
                 tests,
                 configured_failing_tests=(),
                 failfast=False,
                 quiet=False,
                 configured_run_alone_tests=(),
                 worker_count=DEFAULT_NWORKERS,
                 second_chance=False):
        """
        :keyword quiet: Set to True or False to explicitly choose. Set to
            `None` to use the default, which may come from the environment variable
            ``GEVENTTEST_QUIET``.
        """
        self._tests = tests
        self._configured_failing_tests = configured_failing_tests
        self._quiet = quiet
        self._configured_run_alone_tests = configured_run_alone_tests

        assert not (failfast and second_chance)
        self._failfast = failfast
        self._second_chance = second_chance

        self.results = ResultCollector()
        self.results.total = len(self._tests)
        self._running_jobs = []

        self._worker_count = min(len(tests), worker_count) or 1

    def _run_one(self, cmd, **kwargs):
        if self._quiet is not None:
            kwargs['quiet'] = self._quiet
        result = util.run(cmd, **kwargs)
        if not result and self._second_chance:
            self.results <<= result
            util.log("> %s", result.name, color='warning')
            result = util.run(cmd, **kwargs)
        if not result and self._failfast:
            # Under Python 3.9 (maybe older versions?), raising the
            # SystemExit here (a background thread belonging to the
            # pool) doesn't seem to work well. It gets stuck waiting
            # for a lock? The job never shows up as finished.
            raise FailFast(cmd)
        self.results += result

    def _reap(self):
        "Clean up the list of running jobs, returning how many are still outstanding."
        for r in self._running_jobs[:]:
            if not r.ready():
                continue
            if r.successful():
                self._running_jobs.remove(r)
            else:
                r.get()
                sys.exit('Internal error in testrunner.py: %r' % (r, ))
        return len(self._running_jobs)

    def _reap_all(self):
        util.log("Reaping %d jobs", len(self._running_jobs), color="debug")
        while self._running_jobs:
            if not self._reap():
                break
            util.sleep(self.TIME_WAIT_REAP)

    def _spawn(self, pool, cmd, options):
        while True:
            if self._reap() < self._worker_count:
                job = pool.apply_async(self._run_one, (cmd, ), options or {})
                self._running_jobs.append(job)
                return

            util.sleep(self.TIME_WAIT_SPAWN)

    def __call__(self):
        util.log("Running tests in parallel with concurrency %s %s." % (
            self._worker_count,
            util._colorize('number', '(concurrency available: %d)' % AVAIL_NWORKERS)
        ),)
        # Setting global state, in theory we can be used multiple times.
        # This is fine as long as we are single threaded and call these
        # sequentially.
        util.BUFFER_OUTPUT = self._worker_count > 1 or self._quiet

        start = util.perf_counter()
        try:
            self._run_tests()
        except KeyboardInterrupt:
            self._report(util.perf_counter() - start, exit=False)
            util.log('(partial results)\n')
            raise
        except:
            traceback.print_exc()
            raise

        self._reap_all()
        self._report(util.perf_counter() - start, exit=True)

    def _run_tests(self):
        "Runs the tests, produces no report."
        run_alone = []

        tests = self._tests
        pool = ThreadPool(self._worker_count)
        try:
            for cmd, options in tests:
                options = options or {}
                if matches(self._configured_run_alone_tests, cmd):
                    run_alone.append((cmd, options))
                else:
                    self._spawn(pool, cmd, options)
            pool.close()
            pool.join()

            if run_alone:
                util.log("Running tests marked standalone")
                for cmd, options in run_alone:
                    self._run_one(cmd, **options)
        except KeyboardInterrupt:
            try:
                util.log('Waiting for currently running to finish...')
                self._reap_all()
            except KeyboardInterrupt:
                pool.terminate()
                raise
        except:
            pool.terminate()
            raise

    def _report(self, elapsed_time, exit=False):
        results = self.results
        report(
            results,
            exit=exit,
            took=elapsed_time,
            configured_failing_tests=self._configured_failing_tests,
        )


class TravisFoldingRunner(object):

    def __init__(self, runner, travis_fold_msg):
        self._runner = runner
        self._travis_fold_msg = travis_fold_msg
        self._travis_fold_name = str(int(util.perf_counter()))

        # A zope-style acquisition proxy would be convenient here.
        run_tests = runner._run_tests

        def _run_tests():
            self._begin_fold()
            try:
                run_tests()
            finally:
                self._end_fold()

        runner._run_tests = _run_tests

    def _begin_fold(self):
        travis.fold_start(self._travis_fold_name,
                          self._travis_fold_msg)

    def _end_fold(self):
        travis.fold_end(self._travis_fold_name)

    def __call__(self):
        return self._runner()


class Discovery(object):
    package_dir = None
    package = None

    def __init__(
            self,
            tests=None,
            ignore_files=None,
            ignored=(),
            coverage=False,
            package=None,
            config=None,
            allow_combine=True,
    ):
        self.config = config or {}
        self.ignore = set(ignored or ())
        self.tests = tests
        self.configured_test_options = config.get('TEST_FILE_OPTIONS', set())
        self.allow_combine = allow_combine
        if ignore_files:
            ignore_files = ignore_files.split(',')
            for f in ignore_files:
                self.ignore.update(set(load_list_from_file(f, package)))

        if coverage:
            self.ignore.update(config.get('IGNORE_COVERAGE', set()))

        if package:
            self.package = package
            self.package_dir = _dir_from_package_name(package)

    class Discovered(object):
        def __init__(self, package, configured_test_options, ignore, config, allow_combine):
            self.orig_dir = os.getcwd()
            self.configured_run_alone = config['RUN_ALONE']
            self.configured_failing_tests = config['FAILING_TESTS']
            self.package = package
            self.configured_test_options = configured_test_options
            self.allow_combine = allow_combine
            self.ignore = ignore

            self.to_import = []
            self.std_monkey_patch_files = []
            self.no_monkey_patch_files = []

            self.commands = []

        @staticmethod
        def __makes_simple_monkey_patch(
                contents,
                _patch_present=re.compile(br'[^#].*patch_all\(\)'),
                _patch_indented=re.compile(br'    .*patch_all\(\)')
        ):
            return (
                # A non-commented patch_all() call is present
                bool(_patch_present.search(contents))
                # that is not indented (because that implies its not at the top-level,
                # so some preconditions are being set)
                and not _patch_indented.search(contents)
            )

        @staticmethod
        def __file_allows_monkey_combine(contents):
            return b'testrunner-no-monkey-combine' not in contents

        @staticmethod
        def __file_allows_combine(contents):
            return b'testrunner-no-combine' not in contents

        @staticmethod
        def __calls_unittest_main_toplevel(
                contents,
                _greentest_main=re.compile(br'    greentest.main\(\)'),
                _unittest_main=re.compile(br'    unittest.main\(\)'),
                _import_main=re.compile(br'from gevent.testing import.*main'),
                _main=re.compile(br'    main\(\)'),
        ):
            # TODO: Add a check that this comes in a line directly after
            # if __name__ == __main__.
            return (
                _greentest_main.search(contents)
                or _unittest_main.search(contents)
                or (_import_main.search(contents) and _main.search(contents))
            )

        def __has_config(self, filename):
            return (
                RUN_LEAKCHECKS
                or filename in self.configured_test_options
                or filename in self.configured_run_alone
                or matches(self.configured_failing_tests, filename)
            )

        def __can_monkey_combine(self, filename, contents):
            return (
                self.allow_combine
                and not self.__has_config(filename)
                and self.__makes_simple_monkey_patch(contents)
                and self.__file_allows_monkey_combine(contents)
                and self.__file_allows_combine(contents)
                and self.__calls_unittest_main_toplevel(contents)
            )

        @staticmethod
        def __makes_no_monkey_patch(contents, _patch_present=re.compile(br'[^#].*patch_\w*\(')):
            return not _patch_present.search(contents)

        def __can_nonmonkey_combine(self, filename, contents):
            return (
                self.allow_combine
                and not self.__has_config(filename)
                and self.__makes_no_monkey_patch(contents)
                and self.__file_allows_combine(contents)
                and self.__calls_unittest_main_toplevel(contents)
            )

        def __begin_command(self):
            cmd = [sys.executable, '-u']
            # XXX: -X track-resources is broken. This happened when I updated to
            # PyPy 7.3.2. It started failing to even start inside the virtual environment
            # with
            #
            # debug: OperationError:
            # debug:  operror-type: ImportError
            # debug:  operror-value: No module named traceback
            #
            # I don't know if this is PyPy's problem or a problem in virtualenv:
            #
            # virtualenv==20.0.35
            # virtualenv-clone==0.5.4
            # virtualenvwrapper==4.8.4
            #
            # Deferring investigation until I need this...

            # if PYPY and PY2:
            #     # Doesn't seem to be an env var for this.
            #     # XXX: track-resources is broken in virtual environments
            #     # on 7.3.2.
            #     cmd.extend(('-X', 'track-resources'))
            return cmd


        def __add_test(self, qualified_name, filename, contents):
            if b'TESTRUNNER' in contents: # test__monkey_patching.py
                # XXX: Rework this to avoid importing.
                # XXX: Rework this to allow test combining (it could write the files out and return
                # them directly; we would use 'python -m gevent.monkey --module unittest ...)
                self.to_import.append(qualified_name)
            elif self.__can_monkey_combine(filename, contents):
                self.std_monkey_patch_files.append(qualified_name if self.package else filename)
            elif self.__can_nonmonkey_combine(filename, contents):
                self.no_monkey_patch_files.append(qualified_name if self.package else filename)
            else:
                # XXX: For simple python module tests, try this with
                # `runpy.run_module`, very similar to the way we run
                # things for monkey patching. The idea here is that we
                # can perform setup ahead of time (e.g.,
                # setup_resources()) in each test without having to do
                # it manually or force calls or modifications to those
                # tests.
                cmd = self.__begin_command()
                if self.package:
                    # Using a package is the best way to work with coverage 5
                    # when we specify 'source = <package>'
                    cmd.append('-m' + qualified_name)
                else:
                    cmd.append(filename)

                options = DEFAULT_RUN_OPTIONS.copy()
                options.update(self.configured_test_options.get(filename, {}))
                self.commands.append((cmd, options))

        @staticmethod
        def __remove_options(lst):
            return [x for x in lst if x and not x.startswith('-')]

        def __expand_imports(self):
            for qualified_name in self.to_import:
                module = importlib.import_module(qualified_name)
                for cmd, options in module.TESTRUNNER():
                    if self.__remove_options(cmd)[-1] in self.ignore:
                        continue
                    self.commands.append((cmd, options))
            del self.to_import[:]

        def __combine_commands(self, files, group_size=5):
            if not files:
                return

            from itertools import groupby
            cnt = [0, 0]
            def make_group(_):
                if cnt[0] > group_size:
                    cnt[0] = 0
                    cnt[1] += 1
                cnt[0] += 1
                return cnt[1]

            for _, group in groupby(files, make_group):

                cmd = self.__begin_command()
                cmd.append('-m')
                cmd.append('unittest')
                # cmd.append('-v')
                for name in group:
                    cmd.append(name)
                self.commands.insert(0, (cmd, DEFAULT_RUN_OPTIONS.copy()))

            del files[:]


        def visit_file(self, filename):
            # Support either 'gevent.tests.foo' or 'gevent/tests/foo.py'
            if filename.startswith('gevent.tests'):
                # XXX: How does this interact with 'package'? Probably not well
                qualified_name = module_name = filename
                filename = filename[len('gevent.tests') + 1:]
                filename = filename.replace('.', os.sep) + '.py'
            else:
                module_name = os.path.splitext(filename)[0]
                qualified_name = self.package + '.' + module_name if self.package else module_name

            # Also allow just 'foo' as a shortcut for 'gevent.tests.foo'
            abs_filename = os.path.abspath(filename)
            if (
                    not os.path.exists(abs_filename)
                    and not filename.endswith('.py')
                    and os.path.exists(abs_filename + '.py') ):
                abs_filename = abs_filename + '.py'

            with open(abs_filename, 'rb') as f:
                # Some of the test files (e.g., test__socket_dns) are
                # UTF8 encoded. Depending on the environment, Python 3 may
                # try to decode those as ASCII, which fails with UnicodeDecodeError.
                # Thus, be sure to open and compare in binary mode.
                # Open the absolute path to make errors more clear,
                # but we can't store the absolute path, our configuration is based on
                # relative file names.
                contents = f.read()

            self.__add_test(qualified_name, filename, contents)

        def visit_files(self, filenames):
            for filename in filenames:
                self.visit_file(filename)
            with Discovery._in_dir(self.orig_dir):
                self.__expand_imports()
            self.__combine_commands(self.std_monkey_patch_files)
            self.__combine_commands(self.no_monkey_patch_files)

    @staticmethod
    @contextmanager
    def _in_dir(package_dir):
        olddir = os.getcwd()
        if package_dir:
            os.chdir(package_dir)
        try:
            yield
        finally:
            os.chdir(olddir)

    @Lazy
    def discovered(self):
        tests = self.tests
        discovered = self.Discovered(self.package, self.configured_test_options,
                                     self.ignore, self.config, self.allow_combine)

        # We need to glob relative names, our config is based on filenames still
        with self._in_dir(self.package_dir):
            if not tests:
                tests = set(glob.glob('test_*.py')) - set(['test_support.py'])
            else:
                tests = set(tests)

            if self.ignore:
                # Always ignore the designated list, even if tests
                # were specified on the command line. This fixes a
                # nasty interaction with
                # test__threading_vs_settrace.py being run under
                # coverage when 'grep -l subprocess test*py' is used
                # to list the tests to run.
                tests -= self.ignore
            tests = sorted(tests)
            discovered.visit_files(tests)

        return discovered

    def __iter__(self):
        return iter(self.discovered.commands) # pylint:disable=no-member

    def __len__(self):
        return len(self.discovered.commands) # pylint:disable=no-member

def load_list_from_file(filename, package):
    result = []
    if filename:
        # pylint:disable=unspecified-encoding
        with open(_package_relative_filename(filename, package)) as f:
            for x in f:
                x = x.split('#', 1)[0].strip()
                if x:
                    result.append(x)
    return result


def matches(possibilities, command, include_flaky=True):
    if isinstance(command, list):
        command = ' '.join(command)
    for line in possibilities:
        if not include_flaky and line.startswith('FLAKY '):
            continue
        line = line.replace('FLAKY ', '')
        # Our configs are still mostly written in terms of file names,
        # but the non-monkey tests are now using package names.
        # Strip off '.py' from filenames to see if we match a module.
        # XXX: This could be much better. Our command needs better structure.
        if command.endswith(' ' + line) or command.endswith(line.replace(".py", '')):
            return True
        if ' '  not in command and command == line:
            return True
    return False


def format_seconds(seconds):
    if seconds < 20:
        return '%.1fs' % seconds
    seconds = str(timedelta(seconds=round(seconds)))
    if seconds.startswith('0:'):
        seconds = seconds[2:]
    return seconds


def _show_longest_running(result_collector, how_many=5):
    longest_running_tests = result_collector.longest_running_tests
    if not longest_running_tests:
        return
    # The only tricky part is handling repeats. we want to show them,
    # but not count them as a distinct entry.

    util.log('\nLongest-running tests:')
    length_of_longest_formatted_decimal = len('%.1f' % longest_running_tests[0].run_duration)

    frmt = '%' + str(length_of_longest_formatted_decimal) + '.1f seconds: %s'
    seen_names = set()
    for result in longest_running_tests:
        util.log(frmt, result.run_duration, result.name)
        seen_names.add(result.name)
        if len(seen_names) >= how_many:
            break



def report(result_collector, # type: ResultCollector
           exit=True, took=None,
           configured_failing_tests=()):
    # pylint:disable=redefined-builtin,too-many-branches,too-many-locals
    total = result_collector.total
    failed = result_collector.failed
    passed = result_collector.passed
    total_cases = result_collector.total_cases
    total_skipped = result_collector.total_skipped

    _show_longest_running(result_collector)

    if took:
        took = ' in %s' % format_seconds(took)
    else:
        took = ''

    failed_expected = []
    failed_unexpected = []
    passed_unexpected = []

    for name in passed:
        if matches(configured_failing_tests, name, include_flaky=False):
            passed_unexpected.append(name)

    if passed_unexpected:
        util.log('\n%s/%s unexpected passes', len(passed_unexpected), total, color='error')
        print_list(passed_unexpected)

    if result_collector.reran:
        util.log('\n%s/%s tests rerun', len(result_collector.reran), total, color='warning')
        print_list(result_collector.reran)

    if failed:
        util.log('\n%s/%s tests failed%s', len(failed), total, took, color='warning')

        for name in failed:
            if matches(configured_failing_tests, name, include_flaky=True):
                failed_expected.append(name)
            else:
                failed_unexpected.append(name)

        if failed_expected:
            util.log('\n%s/%s expected failures', len(failed_expected), total, color='warning')
            print_list(failed_expected)

        if failed_unexpected:
            util.log('\n%s/%s unexpected failures', len(failed_unexpected), total, color='error')
            print_list(failed_unexpected)

    util.log(
        '\nRan %s tests%s in %s files%s',
        total_cases,
        util._colorize('skipped', " (skipped=%d)" % total_skipped) if total_skipped else '',
        total,
        took,
    )

    if exit:
        if failed_unexpected:
            sys.exit(min(100, len(failed_unexpected)))
        if passed_unexpected:
            sys.exit(101)
        if total <= 0:
            sys.exit('No tests found.')


def print_list(lst):
    for name in lst:
        util.log(' - %s', name)

def _setup_environ(debug=False):
    def not_set(key):
        return not bool(os.environ.get(key))

    if (not_set('PYTHONWARNINGS')
            and (not sys.warnoptions
                 # Python 3.7 goes from [] to ['default'] for nothing
                 or sys.warnoptions == ['default'])):
        # action:message:category:module:line

        # - when a warning matches
        #   more than one option, the action for the last matching
        #   option is performed.
        # - action is one of : ignore, default, all, module, once, error

        # Enable default warnings such as ResourceWarning.
        # ResourceWarning doesn't exist on Py2, so don't put it
        # in there to avoid a warnnig.
        defaults = [
            'default',
            'default::DeprecationWarning',
        ]
        if not PY2:
            defaults.append('default::ResourceWarning')

        os.environ['PYTHONWARNINGS'] = ','.join(defaults + [
            # On Python 3[.6], the system site.py module has
            # "open(fullname, 'rU')" which produces the warning that
            # 'U' is deprecated, so ignore warnings from site.py
            'ignore:::site:',
            # pkgutil on Python 2 complains about missing __init__.py
            'ignore:::pkgutil:',
            # importlib/_bootstrap.py likes to spit out "ImportWarning:
            # can't resolve package from __spec__ or __package__, falling
            # back on __name__ and __path__". I have no idea what that means, but it seems harmless
            # and is annoying.
            'ignore:::importlib._bootstrap:',
            'ignore:::importlib._bootstrap_external:',
            # importing ABCs from collections, not collections.abc
            'ignore:::pkg_resources._vendor.pyparsing:',
            'ignore:::dns.namedict:',
            # dns.hash itself is being deprecated, importing it raises the warning;
            # we don't import it, but dnspython still does
            'ignore:::dns.hash:',
            # dns.zone uses some raw regular expressions
            # without the r'' syntax, leading to DeprecationWarning: invalid
            # escape sequence. This is fixed in 2.0 (Python 3 only).
            'ignore:::dns.zone:',
        ])

    if not_set('PYTHONFAULTHANDLER'):
        os.environ['PYTHONFAULTHANDLER'] = 'true'

    if not_set('GEVENT_DEBUG') and debug:
        os.environ['GEVENT_DEBUG'] = 'debug'

    if not_set('PYTHONTRACEMALLOC') and debug:
        # This slows the tests down quite a bit. Reserve
        # for debugging.
        os.environ['PYTHONTRACEMALLOC'] = '10'

    if not_set('PYTHONDEVMODE'):
        # Python 3.7 and above.
        os.environ['PYTHONDEVMODE'] = '1'

    if not_set('PYTHONMALLOC') and debug:
        # Python 3.6 and above.
        # This slows the tests down some, but
        # can detect memory corruption. Unfortunately
        # it can also be flaky, especially in pre-release
        # versions of Python (e.g., lots of crashes on Python 3.8b4).
        os.environ['PYTHONMALLOC'] = 'debug'

    if sys.version_info.releaselevel != 'final' and not debug:
        os.environ['PYTHONMALLOC'] = 'default'
        os.environ['PYTHONDEVMODE'] = ''

    interesting_envs = {
        k: os.environ[k]
        for k in os.environ
        if k.startswith(('PYTHON', 'GEVENT'))
    }
    widest_k = max(len(k) for k in interesting_envs)
    for k, v in sorted(interesting_envs.items()):
        util.log('%*s\t=\t%s', widest_k, k, v, color="debug")


def main():
    # pylint:disable=too-many-locals,too-many-statements
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--ignore')
    parser.add_argument(
        '--discover', action='store_true',
        help="Only print the tests found."
    )
    parser.add_argument(
        '--config', default='known_failures.py',
        help="The path to the config file containing "
        "FAILING_TESTS, IGNORED_TESTS and RUN_ALONE. "
        "Defaults to %(default)s."
    )
    parser.add_argument(
        "--coverage", action="store_true",
        help="Enable coverage recording with coverage.py."
    )
    # TODO: Quiet and verbose should be mutually exclusive
    parser.add_argument(
        "--quiet", action="store_true", default=True,
        help="Be quiet. Defaults to %(default)s. Also the "
        "GEVENTTEST_QUIET environment variable."
    )
    parser.add_argument("--verbose", action="store_false", dest='quiet')

    parser.add_argument(
        "--debug", action="store_true", default=False,
        help="Enable debug settings. If the GEVENT_DEBUG environment variable is not set, "
        "this sets it to 'debug'. This can also enable PYTHONTRACEMALLOC and the debug PYTHONMALLOC "
        "allocators, if not already set. Defaults to %(default)s."
     )

    parser.add_argument(
        "--package", default="gevent.tests",
        help="Load tests from the given package. Defaults to %(default)s."
    )
    parser.add_argument(
        "--processes", "-j", default=DEFAULT_NWORKERS, type=int,
        help="Use up to the given number of parallel processes to execute tests. "
        "Defaults to %(default)s."
    )
    parser.add_argument(
        '--no-combine', default=True, action='store_false',
        help="Do not combine tests into process groups."
    )
    parser.add_argument('-u', '--use', metavar='RES1,RES2,...',
                        action='store', type=parse_resources,
                        help='specify which special resource intensive tests '
                        'to run. "all" is the default; "none" may also be used. '
                        'Disable individual resources with a leading -.'
                        'For example, "-u-network". GEVENTTEST_USE_RESOURCES is used '
                        'if no argument is given. To only use one resources, specify '
                        '"-unone,resource".')
    parser.add_argument("--travis-fold", metavar="MSG",
                        help="Emit Travis CI log fold markers around the output.")

    fail_parser = parser.add_mutually_exclusive_group()
    fail_parser.add_argument(
        "--second-chance", action="store_true", default=False,
        help="Give failed tests a second chance.")
    fail_parser.add_argument(
        '--failfast', '-x', action='store_true', default=False,
        help="Stop running after the first failure.")

    parser.add_argument('tests', nargs='*')
    options = parser.parse_args()
    # options.use will be either None for not given, or a list
    # of the last specified -u argument.
    # If not given, use the default, which we'll take from the environment, if set.
    options.use = list(set(parse_resources() if options.use is None else options.use))

    # Whether or not it came from the environment, put it in the
    # environment now.
    os.environ['GEVENTTEST_USE_RESOURCES'] = unparse_resources(options.use)
    setup_resources(options.use)


    # Set this before any test imports in case of 'from .util import QUIET';
    # not that this matters much because we spawn tests in subprocesses,
    # it's the environment setting that matters
    util.QUIET = options.quiet
    if 'GEVENTTEST_QUIET' not in os.environ:
        os.environ['GEVENTTEST_QUIET'] = str(options.quiet)

    FAILING_TESTS = []
    IGNORED_TESTS = []
    RUN_ALONE = []

    coverage = False
    if options.coverage or os.environ.get("GEVENTTEST_COVERAGE"):
        if PYPY and RUNNING_ON_CI:
            print("Ignoring coverage option on PyPy on CI; slow")
        else:
            coverage = True
            cov_config = os.environ['COVERAGE_PROCESS_START'] = os.path.abspath(".coveragerc")
            if PYPY:
                cov_config = os.environ['COVERAGE_PROCESS_START'] = os.path.abspath(".coveragerc-pypy")

            this_dir = os.path.dirname(__file__)
            site_dir = os.path.join(this_dir, 'coveragesite')
            site_dir = os.path.abspath(site_dir)
            os.environ['PYTHONPATH'] = site_dir + os.pathsep + os.environ.get("PYTHONPATH", "")
            # We change directory often, use an absolute path to keep all the
            # coverage files (which will have distinct suffixes because of parallel=true in .coveragerc
            # in this directory; makes them easier to combine and use with coverage report)
            os.environ['COVERAGE_FILE'] = os.path.abspath(".") + os.sep + ".coverage"
            # XXX: Log this with color. Right now, it interferes (buffering) with other early
            # output.
            print("Enabling coverage to", os.environ['COVERAGE_FILE'],
                  "with site", site_dir,
                  "and configuration file", cov_config)
            assert os.path.exists(cov_config)
            assert os.path.exists(os.path.join(site_dir, 'sitecustomize.py'))

    _setup_environ(debug=options.debug)

    if options.config:
        config = {}
        options.config = _package_relative_filename(options.config, options.package)
        with open(options.config) as f: # pylint:disable=unspecified-encoding
            config_data = f.read()
        six.exec_(config_data, config)
        FAILING_TESTS = config['FAILING_TESTS']
        IGNORED_TESTS = config['IGNORED_TESTS']
        RUN_ALONE = config['RUN_ALONE']

    tests = Discovery(
        options.tests,
        ignore_files=options.ignore,
        ignored=IGNORED_TESTS,
        coverage=coverage,
        package=options.package,
        config=config,
        allow_combine=options.no_combine,
    )
    if options.discover:
        for cmd, options in tests:
            print(util.getname(cmd, env=options.get('env'), setenv=options.get('setenv')))
        print('%s tests found.' % len(tests))
    else:
        if PYPY and RESOLVER_ARES:
            # XXX: Add a way to force these.
            print("Not running tests on pypy with c-ares; not a supported configuration")
            return
        if options.package:
            # Put this directory on the path so relative imports work.
            package_dir = _dir_from_package_name(options.package)
            os.environ['PYTHONPATH'] = os.environ.get('PYTHONPATH', "") + os.pathsep + package_dir
        runner = Runner(
            tests,
            configured_failing_tests=FAILING_TESTS,
            failfast=options.failfast,
            quiet=options.quiet,
            configured_run_alone_tests=RUN_ALONE,
            worker_count=options.processes,
            second_chance=options.second_chance,
        )

        if options.travis_fold:
            runner = TravisFoldingRunner(runner, options.travis_fold)

        runner()


if __name__ == '__main__':
    main()
