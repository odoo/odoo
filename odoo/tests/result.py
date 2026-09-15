import collections
import contextlib
import inspect
import logging
import re
import sys
import time
import traceback
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol

from .. import db
from ..libs.debug_log import DebugLog
from ..tools import config
from . import case
from .utils import env_int

if TYPE_CHECKING:
    import types
    from collections.abc import Generator

__unittest = True

_debug = DebugLog(__name__)

_max_failed = env_int("ODOO_TEST_MAX_FAILED_TESTS", 0)
ODOO_TEST_MAX_FAILED_TESTS = _max_failed if _max_failed > 0 else sys.maxsize

REQUIRE_INFRA = bool(env_int("ODOO_REQUIRE_INFRA", 1))
"""Require selected tests to have their infrastructure unless explicitly opted out."""

stats_logger = logging.getLogger("odoo.tests.stats")


class Stat(NamedTuple):
    time: float = 0.0
    queries: int = 0

    def __add__(self, other: object) -> Stat:
        if not isinstance(other, Stat):
            return NotImplemented

        return Stat(
            self.time + other.time,
            self.queries + other.queries,
        )


_logger = logging.getLogger(__name__)
_TEST_ID = re.compile(
    r"""
^
odoo\.addons\.
(?P<module>[^.]+)
\.tests\.
(?P<class>.+)
\.
(?P<method>[^.]+)
$
""",
    re.VERBOSE,
)


class TestLike(Protocol):
    failureException: Any

    def id(self) -> str: ...

    def shortDescription(self) -> str | None: ...


_ASSERTION_REPORTS: dict[str, OdooTestResult] = {}


def assertion_report(db_name: str) -> OdooTestResult | None:
    if not config["test_enable"]:
        return None
    report = _ASSERTION_REPORTS.get(db_name)
    if report is None:
        report = _ASSERTION_REPORTS[db_name] = OdooTestResult()
        _debug.lifecycle("test.result.report_created", db=db_name)
    return report


def forget_assertion_report(db_name: str | None = None) -> None:
    _debug.lifecycle(
        "test.result.report_forgotten", db=db_name, held=len(_ASSERTION_REPORTS)
    )
    if db_name is None:
        _ASSERTION_REPORTS.clear()
    else:
        _ASSERTION_REPORTS.pop(db_name, None)


class OdooTestResult:
    _monotonic = staticmethod(time.monotonic)

    _previousTestClass: type[case.TestCase] | None = None

    def __init__(
        self,
        stream: Any = None,
        descriptions: Any = None,
        verbosity: Any = None,
        global_report: OdooTestResult | None = None,
    ) -> None:
        self.failures_count = 0
        self.errors_count = 0
        self.testsRun = 0
        self.skipped = 0
        self.infrastructure_skipped = 0
        self.aborted = ""
        self.tb_locals = False
        self.time_start = 0.0
        self.queries_start = 0
        self._soft_fail = False
        self._is_retry = False
        self.had_failure = False
        self.stats: dict[str, Stat] = collections.defaultdict(Stat)
        self.global_report = global_report
        self.shouldStop: bool = bool(global_report and global_report.shouldStop)

    def total_errors_count(self) -> int:
        result = self.errors_count + self.failures_count
        if self.global_report:
            result += self.global_report.total_errors_count()
        return result

    def _checkShouldStop(self) -> None:
        if self.total_errors_count() >= ODOO_TEST_MAX_FAILED_TESTS:
            global_report = self.global_report or self
            if not global_report.shouldStop:
                _debug.lifecycle(
                    "test.result.halted",
                    failed=self.total_errors_count(),
                    max=ODOO_TEST_MAX_FAILED_TESTS,
                )
                _logger.error(
                    "Test suite halted: max failed tests already reached (%s). "
                    "Remaining tests will be skipped.",
                    ODOO_TEST_MAX_FAILED_TESTS,
                )
                global_report.shouldStop = True
            self.shouldStop = True

    def printErrors(self) -> None:
        pass

    def startTest(self, test: TestLike) -> None:
        if not self._is_retry:
            self.testsRun += 1
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "test.result.start",
                test=test.id(),
                n=self.testsRun,
                retry=self._is_retry,
                soft=self._soft_fail,
            )
        self.log(
            logging.INFO,
            "Starting %s ...",
            self.getDescription(test),
            test=test,
        )
        self.time_start = self._monotonic()
        self.queries_start = db.sql_counter

    def stopTest(self, test: TestLike) -> None:
        if stats_logger.isEnabledFor(logging.INFO):
            self.stats[test.id()] = Stat(
                time=self._monotonic() - self.time_start,
                queries=db.sql_counter - self.queries_start,
            )
        if _debug.perf.enabled:
            _debug.perf.count(
                "test.result.stop",
                test=test.id(),
                ms=(self._monotonic() - self.time_start) * 1000.0,
                queries=db.sql_counter - self.queries_start,
                retry=self._is_retry,
            )

    def _record_failure(self, counter: str) -> None:
        if self._soft_fail:
            self.had_failure = True
        else:
            setattr(self, counter, getattr(self, counter) + 1)
        _debug.lifecycle(
            "test.result.failure_recorded",
            counter=counter,
            soft=self._soft_fail,
            failures=self.failures_count,
            errors=self.errors_count,
        )
        self._checkShouldStop()

    def addError(self, test: TestLike, err: tuple) -> None:
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "test.result.error",
                test=test.id(),
                error=err[0].__name__ if err[0] else None,
                soft=self._soft_fail,
            )
        self.logError("ERROR", test, err)
        self._record_failure("errors_count")

    def addFailure(self, test: TestLike, err: tuple) -> None:
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "test.result.fail",
                test=test.id(),
                error=err[0].__name__ if err[0] else None,
                soft=self._soft_fail,
            )
        self.logError("FAIL", test, err)
        self._record_failure("failures_count")

    def addSubTest(
        self, test: case.TestCase, subtest: TestLike, err: tuple | None
    ) -> None:
        if err is not None:
            is_failure = issubclass(err[0], test.failureException)
            if _debug.logic.enabled:
                _debug.logic(
                    "test.result.subtest_failed",
                    test=subtest.id(),
                    failure=is_failure,
                )
            if is_failure:
                self.addFailure(subtest, err)
            else:
                self.addError(subtest, err)

    def addSuccess(self, test: TestLike) -> None:
        if _debug.lifecycle.enabled:
            _debug.lifecycle("test.result.success", test=test.id())

    def addSkip(
        self, test: TestLike, reason: str, infrastructure: bool = False
    ) -> None:
        self.skipped += 1
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "test.result.skip",
                test=test.id(),
                infrastructure=infrastructure,
                require_infra=REQUIRE_INFRA,
                skipped=self.skipped,
            )
        if not infrastructure:
            self.log(
                logging.INFO,
                "skipped %s : %s",
                self.getDescription(test),
                reason,
                test=test,
            )
            return

        self.infrastructure_skipped += 1
        if REQUIRE_INFRA:
            self.log(
                logging.ERROR,
                "INFRASTRUCTURE UNAVAILABLE %s : %s (ODOO_REQUIRE_INFRA=1)",
                self.getDescription(test),
                reason,
                test=test,
            )
            self._record_failure("errors_count")
        else:
            self.log(
                logging.WARNING,
                "skipped %s : %s (environment cannot run it; "
                "ODOO_REQUIRE_INFRA=0 explicitly permits this incomplete run)",
                self.getDescription(test),
                reason,
                test=test,
            )

    def wasSuccessful(self) -> bool:
        return self.failures_count == self.errors_count == 0

    def record_abort(self, reason: str) -> None:
        self.aborted = reason
        self.errors_count += 1
        _debug.lifecycle("test.result.aborted", reason=reason)

    def _exc_info_to_string(self, err: tuple, test: TestLike) -> str:
        exctype, value, tb = err
        while tb and self._is_relevant_tb_level(tb):
            tb = tb.tb_next

        if exctype is test.failureException:
            length = self._count_relevant_tb_levels(tb)
        else:
            length = None
        tb_e = traceback.TracebackException(
            exctype, value, tb, limit=length, capture_locals=self.tb_locals
        )
        msgLines = list(tb_e.format())

        return "".join(msgLines)

    def _is_relevant_tb_level(self, tb: types.TracebackType) -> bool:
        return "__unittest" in tb.tb_frame.f_globals

    def _count_relevant_tb_levels(self, tb: types.TracebackType | None) -> int:
        length = 0
        while tb and not self._is_relevant_tb_level(tb):
            length += 1
            tb = tb.tb_next
        return length

    def __repr__(self):
        return f"<{self.__class__.__module__}.{self.__class__.__qualname__} run={self.testsRun} errors={self.errors_count} failures={self.failures_count}>"

    def __str__(self):
        summary = (
            f"{self.failures_count} failed, {self.errors_count} error(s) "
            f"of {self.testsRun} tests"
        )
        if self.infrastructure_skipped:
            summary += (
                f" ({self.infrastructure_skipped} skipped because the "
                f"environment could not run them)"
            )
        if self.aborted:
            summary += f", run aborted before it finished: {self.aborted}"
        return summary

    @contextlib.contextmanager
    def retry(self) -> Generator[None]:
        previous = self._is_retry
        self._is_retry = True
        _debug.lifecycle("test.result.retry_enter", nested=previous)
        try:
            yield
        finally:
            self._is_retry = previous
            _debug.lifecycle("test.result.retry_exit")

    @contextlib.contextmanager
    def soft_fail(self) -> Generator[None]:
        self.had_failure = False
        self._soft_fail = True
        _debug.lifecycle("test.result.soft_fail_enter")
        try:
            yield
        finally:
            self._soft_fail = False
            _debug.lifecycle("test.result.soft_fail_exit", had_failure=self.had_failure)

    def update(self, other: OdooTestResult) -> None:
        self.failures_count += other.failures_count
        self.errors_count += other.errors_count
        self.testsRun += other.testsRun
        self.skipped += other.skipped
        self.infrastructure_skipped += other.infrastructure_skipped
        self.aborted = self.aborted or other.aborted
        for test_id, stat in other.stats.items():
            self.stats[test_id] += stat
        _debug.pipeline(
            "test.result.merged",
            tests=other.testsRun,
            failures=other.failures_count,
            errors=other.errors_count,
            skipped=other.skipped,
            stats=len(other.stats),
            total=self.testsRun,
        )

    def log(
        self,
        level: int,
        msg: str,
        *args: Any,
        test: TestLike | None = None,
        exc_info: Any = None,
        extra: dict | None = None,
        stack_info: bool = False,
        caller_infos: tuple | None = None,
    ) -> None:
        source: TestLike | OdooTestResult = test or self
        while isinstance(source, case._SubTest) and source.test_case:
            source = source.test_case
        logger = logging.getLogger(source.__module__)
        try:
            caller_infos = caller_infos or logger.findCaller(stack_info)
        except ValueError:
            caller_infos = "(unknown file)", 0, "(unknown function)", None
        fn, lno, func, sinfo = caller_infos
        if logger.isEnabledFor(level):
            record = logger.makeRecord(
                logger.name,
                level,
                fn,
                lno,
                msg,
                args,
                exc_info,
                func,
                extra,
                sinfo,
            )
            logger.handle(record)

    def log_stats(self) -> None:
        if not stats_logger.isEnabledFor(logging.INFO):
            return

        details = stats_logger.isEnabledFor(logging.DEBUG)
        stats_tree: dict[str, Stat] = collections.defaultdict(Stat)
        counts: collections.Counter[str] = collections.Counter()
        unmatched = 0  # debuglog
        for test, stat in self.stats.items():
            r = _TEST_ID.match(test)
            if not r:
                unmatched += 1  # debuglog
                continue

            stats_tree[r["module"]] += stat
            counts[r["module"]] += 1
            if details:
                stats_tree[f"{r['module']}.{r['class']}"] += stat
                stats_tree[f"{r['module']}.{r['class']}.{r['method']}"] += stat

        _debug.pipeline(
            "test.result.log_stats",
            entries=len(self.stats),
            modules=len(counts),
            unmatched=unmatched,
            details=details,
        )
        if details:
            stats_logger.debug(
                "Detailed Tests Report:\n%s",
                "".join(
                    f"\t{test}: {stats.time:.2f}s {stats.queries} queries\n"
                    for test, stats in sorted(stats_tree.items())
                ),
            )
        else:
            for module, stat in sorted(stats_tree.items()):
                stats_logger.info(
                    "%s: %d tests %.2fs %d queries",
                    module,
                    counts[module],
                    stat.time,
                    stat.queries,
                )

    def getDescription(self, test: TestLike) -> str:
        if isinstance(test, case._SubTest):
            tc = test.test_case
            return (
                f"Subtest {tc.__class__.__qualname__}"
                f".{tc._testMethodName} {test._subDescription()}"
            )
        if isinstance(test, case.TestCase):
            return f"{test.__class__.__qualname__}.{test._testMethodName}"
        return str(test)

    @contextlib.contextmanager
    def collectStats(self, test_id: str) -> Generator[None]:
        queries_before = db.sql_counter
        time_start = self._monotonic()

        try:
            yield
        finally:
            stat = Stat(
                time=self._monotonic() - time_start,
                queries=db.sql_counter - queries_before,
            )
            self.stats[test_id] += stat
            _debug.perf.count(
                "test.result.stats",
                id=test_id,
                ms=stat.time * 1000.0,
                queries=stat.queries,
            )

    def logError(self, flavour: str, test: TestLike, error: tuple) -> None:
        err = self._exc_info_to_string(error, test)
        caller_infos = self.getErrorCallerInfo(error, test)
        _debug.pipeline(
            "test.result.error_logged",
            flavour=flavour,
            located=caller_infos is not None,
            lines=err.count("\n"),
        )
        self.log(logging.INFO, "=" * 70, test=test, caller_infos=caller_infos)
        self.log(
            logging.ERROR,
            "%s: %s\n%s",
            flavour,
            self.getDescription(test),
            err,
            test=test,
            caller_infos=caller_infos,
        )

    def getErrorCallerInfo(
        self, error: tuple, test: TestLike
    ) -> tuple[str, int, str, None] | None:

        if not isinstance(test, case.TestCase):
            return None

        _, _, error_traceback = error

        while isinstance(test, case._SubTest) and test.test_case:
            test = test.test_case

        method_tb = None
        file_tb = None
        try:
            filename = inspect.getfile(type(test))
        except OSError, TypeError:
            filename = None

        while error_traceback:
            code = error_traceback.tb_frame.f_code
            if code.co_name in (test._testMethodName, "setUp", "tearDown"):
                method_tb = error_traceback
            if code.co_filename == filename:
                file_tb = error_traceback
            error_traceback = error_traceback.tb_next

        infos_tb = method_tb or file_tb
        _debug.logic(
            "test.result.caller_info",
            source="method" if method_tb else "file" if file_tb else None,
            file_known=filename is not None,
        )
        if infos_tb:
            code = infos_tb.tb_frame.f_code
            lineno = infos_tb.tb_lineno
            filename = code.co_filename
            method = test._testMethodName
            return (filename, lineno, method, None)
        return None
