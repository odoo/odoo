"""Test result object"""

import logging
import collections
import contextlib
import inspect
import re
import time
import traceback

from typing import NamedTuple

from . import case
from .. import sql_db

__unittest = True

STDOUT_LINE = '\nStdout:\n%s'
STDERR_LINE = '\nStderr:\n%s'


stats_logger = logging.getLogger('odoo.tests.stats')


class Stat(NamedTuple):
    time: float = 0.0
    queries: int = 0

    def __add__(self, other: 'Stat') -> 'Stat':
        if other == 0:
            return self

        if not isinstance(other, Stat):
            return NotImplemented

        return Stat(
            self.time + other.time,
            self.queries + other.queries,
        )

_logger = logging.getLogger(__name__)
_TEST_ID = re.compile(r"""
^
odoo\.addons\.
(?P<module>[^.]+)
\.tests\.
(?P<class>.+)
\.
(?P<method>[^.]+)
$
""", re.VERBOSE)


class OdooTestResult(object):
    """
    This class in inspired from TextTestResult and modifies TestResult
    Instead of using a stream, we are using the logger.

    unittest.TestResult: Holder for test result information.

    Test results are automatically managed by the TestCase and TestSuite
    classes, and do not need to be explicitly manipulated by writers of tests.

    This version does not hold a list of failure but just a count since the failure is logged immediately
    This version is also simplied to better match our use cases
    """

    _previousTestClass = None
    _moduleSetUpFailed = False

    def __init__(self, stream=None, descriptions=None, verbosity=None):
        self.failures_count = 0
        self.errors_count = 0
        self.testsRun = 0
        self.skipped = 0
        self.tb_locals = False
        # custom
        self.time_start = None
        self.queries_start = None
        self._soft_fail = False
        self.had_failure = False
        self.stats = collections.defaultdict(Stat)

    def printErrors(self):
        "Called by TestRunner after test run"

    def startTest(self, test):
        "Called when the given test is about to be run"
        self.testsRun += 1
        self.log(logging.INFO, 'Starting %s ...', self.getDescription(test), test=test)
        self.time_start = time.time()
        self.queries_start = sql_db.sql_counter

    def stopTest(self, test):
        """Called when the given test has been run"""
        if stats_logger.isEnabledFor(logging.INFO):
            self.stats[test.id()] = Stat(
                time=time.time() - self.time_start,
                queries=sql_db.sql_counter - self.queries_start,
            )

    def addError(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        if self._soft_fail:
            self.had_failure = True
        else:
            self.errors_count += 1
        self.logError("ERROR", test, err)

    def addFailure(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info()."""
        if self._soft_fail:
            self.had_failure = True
        else:
            self.failures_count += 1
        self.logError("FAIL", test, err)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            if issubclass(err[0], test.failureException):
                self.addFailure(subtest, err)
            else:
                self.addError(subtest, err)

    def addSuccess(self, test):
        "Called when a test has completed successfully"

    def addSkip(self, test, reason):
        """Called when a test is skipped."""
        self.skipped += 1
        self.log(logging.INFO, 'skipped %s : %s', self.getDescription(test), reason, test=test)

    def wasSuccessful(self):
        """Tells whether or not this result was a success."""
        # The hasattr check is for test_result's OldResult test.  That
        # way this method works on objects that lack the attribute.
        # (where would such result intances come from? old stored pickles?)
        return self.failures_count == self.errors_count == 0

    def _exc_info_to_string(self, err, test):
        """Converts a sys.exc_info()-style tuple of values into a string."""
        exctype, value, tb = err
        # Skip test runner traceback levels
        while tb and self._is_relevant_tb_level(tb):
            tb = tb.tb_next

        if exctype is test.failureException:
            # Skip assert*() traceback levels
            length = self._count_relevant_tb_levels(tb)
        else:
            length = None
        tb_e = traceback.TracebackException(
            exctype, value, tb, limit=length, capture_locals=self.tb_locals)
        msgLines = list(tb_e.format())

        return ''.join(msgLines)

    def _is_relevant_tb_level(self, tb):
        return '__unittest' in tb.tb_frame.f_globals

    def _count_relevant_tb_levels(self, tb):
        length = 0
        while tb and not self._is_relevant_tb_level(tb):
            length += 1
            tb = tb.tb_next
        return length

    def __repr__(self):
        return f"<{self.__class__.__module__}.{self.__class__.__qualname__} run={self.testsRun} errors={self.errors_count} failures={self.failures_count}>"

    def __str__(self):
        return f'{self.failures_count} failed, {self.errors_count} error(s) of {self.testsRun} tests'


    @contextlib.contextmanager
    def soft_fail(self):
        self.had_failure = False
        self._soft_fail = True
        try:
            yield
        finally:
            self._soft_fail = False
            self.had_failure = False

    def update(self, other):
        """ Merges an other test result into this one, only updates contents

        :type other: OdooTestResult
        """
        self.failures_count += other.failures_count
        self.errors_count += other.errors_count
        self.testsRun += other.testsRun
        self.skipped += other.skipped
        self.stats.update(other.stats)

    def log(self, level, msg, *args, test=None, exc_info=None, extra=None, stack_info=False, caller_infos=None):
        """
        ``test`` is the running test case, ``caller_infos`` is
        (fn, lno, func, sinfo) (logger.findCaller format), see logger.log for
        the other parameters.
        """
        test = test or self
        while isinstance(test, case._SubTest) and test.test_case:
            test = test.test_case
        logger = logging.getLogger(test.__module__)
        try:
            caller_infos = caller_infos or logger.findCaller(stack_info)
        except ValueError:
            caller_infos = "(unknown file)", 0, "(unknown function)", None
        (fn, lno, func, sinfo) = caller_infos
        # using logger.log makes it difficult to spot-replace findCaller in
        # order to provide useful location information (the problematic spot
        # inside the test function), so use lower-level functions instead
        if logger.isEnabledFor(level):
            record = logger.makeRecord(logger.name, level, fn, lno, msg, args, exc_info, func, extra, sinfo)
            logger.handle(record)

    def log_stats(self):
        if not stats_logger.isEnabledFor(logging.INFO):
            return

        details = stats_logger.isEnabledFor(logging.DEBUG)
        stats_tree = collections.defaultdict(Stat)
        counts = collections.Counter()
        for test, stat in self.stats.items():
            r = _TEST_ID.match(test)
            if not r: # upgrade has tests at weird paths, ignore them
                continue

            stats_tree[r['module']] += stat
            counts[r['module']] += 1
            if details:
                stats_tree['%(module)s.%(class)s' % r] += stat
                stats_tree['%(module)s.%(class)s.%(method)s' % r] += stat

        if details:
            stats_logger.debug('Detailed Tests Report:\n%s', ''.join(
                f'\t{test}: {stats.time:.2f}s {stats.queries} queries\n'
                for test, stats in sorted(stats_tree.items())
            ))
        else:
            for module, stat in sorted(stats_tree.items()):
                stats_logger.info(
                    "%s: %d tests %.2fs %d queries",
                    module, counts[module],
                    stat.time, stat.queries
                )

    def getDescription(self, test):
        if isinstance(test, case._SubTest):
            return 'Subtest %s.%s %s' % (test.test_case.__class__.__qualname__, test.test_case._testMethodName, test._subDescription())
        if isinstance(test, case.TestCase):
            # since we have the module name in the logger, this will avoid to duplicate module info in log line
            # we only apply this for TestCase since we can receive error handler or other special case
            return "%s.%s" % (test.__class__.__qualname__, test._testMethodName)
        return str(test)

    @contextlib.contextmanager
    def collectStats(self, test_id):
        queries_before = sql_db.sql_counter
        time_start = time.time()

        yield

        self.stats[test_id] += Stat(
            time=time.time() - time_start,
            queries=sql_db.sql_counter - queries_before,
        )

    def logError(self, flavour, test, error):
        err = self._exc_info_to_string(error, test)
        caller_infos = self.getErrorCallerInfo(error, test)
        self.log(logging.INFO, '=' * 70, test=test, caller_infos=caller_infos)  # keep this as info !!!!!!
        self.log(logging.ERROR, "%s: %s\n%s", flavour, self.getDescription(test), err, test=test, caller_infos=caller_infos)

    def getErrorCallerInfo(self, error, test):
        """
        :param error: A tuple (exctype, value, tb) as returned by sys.exc_info().
        :param test: A TestCase that created this error.
        :returns: a tuple (fn, lno, func, sinfo) matching the logger findCaller format or None
        """

        # only handle TestCase here. test can be an _ErrorHolder in some case (setup/teardown class errors)
        if not isinstance(test, case.TestCase):
            return

        _, _, error_traceback = error

        # move upwards the subtest hierarchy to find the real test
        while isinstance(test, case._SubTest) and test.test_case:
            test = test.test_case

        method_tb = None
        file_tb = None
        filename = inspect.getfile(type(test))

        # Note: since _ErrorCatcher was introduced, we could always take the
        # last frame, keeping the check on the test method for safety.
        # Fallbacking on file for cleanup file shoud always be correct to a
        # minimal working version would be
        #
        #   infos_tb = error_traceback
        #   while infos_tb.tb_next()
        #       infos_tb = infos_tb.tb_next()
        #
        while error_traceback:
            code = error_traceback.tb_frame.f_code
            if code.co_name in (test._testMethodName, 'setUp', 'tearDown'):
                method_tb = error_traceback
            if code.co_filename == filename:
                file_tb = error_traceback
            error_traceback = error_traceback.tb_next

        infos_tb = method_tb or file_tb
        if infos_tb:
            code = infos_tb.tb_frame.f_code
            lineno = infos_tb.tb_lineno
            filename = code.co_filename
            method = test._testMethodName
            return (filename, lineno, method, None)
