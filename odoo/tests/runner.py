import collections
import contextlib
import logging
import re
import time
import unittest
from typing import NamedTuple

from .. import sql_db

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
class OdooTestResult(unittest.result.TestResult):
    """
    This class in inspired from TextTestResult (https://github.com/python/cpython/blob/master/Lib/unittest/runner.py)
    Instead of using a stream, we are using the logger,
    but replacing the "findCaller" in order to give the information we
    have based on the test object that is running.
    """

    def __init__(self):
        super().__init__()
        self.time_start = None
        self.queries_start = None
        self._soft_fail = False
        self.had_failure = False
        self.stats = collections.defaultdict(Stat)

    def __str__(self):
        return f'{len(self.failures)} failed, {len(self.errors)} error(s) of {self.testsRun} tests'

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
        self.failures.extend(other.failures)
        self.errors.extend(other.errors)
        self.testsRun += other.testsRun
        self.skipped.extend(other.skipped)
        self.expectedFailures.extend(other.expectedFailures)
        self.unexpectedSuccesses.extend(other.unexpectedSuccesses)
        self.shouldStop = self.shouldStop or other.shouldStop
        self.stats.update(other.stats)

    def log(self, level, msg, *args, test=None, exc_info=None, extra=None, stack_info=False, caller_infos=None):
        """
        ``test`` is the running test case, ``caller_infos`` is
        (fn, lno, func, sinfo) (logger.findCaller format), see logger.log for
        the other parameters.
        """
        test = test or self
        if isinstance(test, unittest.case._SubTest) and test.test_case:
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
        if isinstance(test, unittest.case._SubTest):
            return 'Subtest %s.%s %s' % (test.test_case.__class__.__qualname__, test.test_case._testMethodName, test._subDescription())
        if isinstance(test, unittest.TestCase):
            # since we have the module name in the logger, this will avoid to duplicate module info in log line
            # we only apply this for TestCase since we can receive error handler or other special case
            return "%s.%s" % (test.__class__.__qualname__, test._testMethodName)
        return str(test)

    def startTest(self, test):
        super().startTest(test)
        self.log(logging.INFO, 'Starting %s ...', self.getDescription(test), test=test)
        self.time_start = time.time()
        self.queries_start = sql_db.sql_counter

    def stopTest(self, test):
        if stats_logger.isEnabledFor(logging.INFO):
            self.stats[test.id()] = Stat(
                time=time.time() - self.time_start,
                queries=sql_db.sql_counter - self.queries_start,
            )
        super().stopTest(test)

    @contextlib.contextmanager
    def collectStats(self, test_id):
        queries_before = sql_db.sql_counter
        time_start = time.time()

        yield

        self.stats[test_id] += Stat(
            time=time.time() - time_start,
            queries=sql_db.sql_counter - queries_before,
        )

    def addError(self, test, err):
        if self._soft_fail:
            self.had_failure = True
        else:
            super().addError(test, err)
        self.logError("ERROR", test, err)

    def addFailure(self, test, err):
        if self._soft_fail:
            self.had_failure = True
        else:
            super().addFailure(test, err)
        self.logError("FAIL", test, err)

    def addSubTest(self, test, subtest, err):
        # since addSubTest is not making a call to addFailure or addError we need to manage it too
        # https://github.com/python/cpython/blob/3.7/Lib/unittest/result.py#L136
        if err is not None:
            if issubclass(err[0], test.failureException):
                flavour = "FAIL"
            else:
                flavour = "ERROR"
            self.logError(flavour, subtest, err)
            if self._soft_fail:
                self.had_failure = True
                err = None
        super().addSubTest(test, subtest, err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.log(logging.INFO, 'skipped %s : %s', self.getDescription(test), reason, test=test)

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.log(logging.ERROR, 'unexpected success for %s', self.getDescription(test), test=test)

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

        # only test case should be executed in odoo, this is only a safe guard
        if isinstance(test, unittest.suite._ErrorHolder):
            return
        if not isinstance(test, unittest.TestCase):
            _logger.warning('%r is not a TestCase' % test)
            return
        _, _, error_traceback = error

        while error_traceback:
            code = error_traceback.tb_frame.f_code
            if code.co_name == test._testMethodName:
                lineno = error_traceback.tb_lineno
                filename = code.co_filename
                method = test._testMethodName
                infos = (filename, lineno, method, None)
                return infos
            error_traceback = error_traceback.tb_next
