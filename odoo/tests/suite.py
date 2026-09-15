import contextlib
import logging
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from unittest import BaseTestSuite, util

import odoo
from odoo.libs.debug_log import DebugLog

from .. import db
from . import case
from .case import TestCase
from .http import HttpCase
from .result import OdooTestResult, stats_logger
from .utils import InfrastructureUnavailable

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

__unittest = True

_debug = DebugLog(__name__)


class TestSuite(BaseTestSuite):
    _cleanup: bool
    _removeTestAtIndex: Callable[[int], None]

    def run(  # type: ignore[override]  # this runner requires an OdooTestResult
        self, result: OdooTestResult, debug: bool = False
    ) -> OdooTestResult:
        for index, test in enumerate(self):
            if result.shouldStop:
                _debug.lifecycle("test.suite.halted", at=index, total=len(self._tests))
                break
            assert isinstance(test, TestCase)
            odoo.modules.module.current_test = test
            self._tearDownPreviousClass(test, result)
            self._handleClassSetUp(test, result)
            result._previousTestClass = test.__class__

            if not test.__class__._classSetupFailed:
                test.run(result)
            elif _debug.logic.enabled:
                _debug.logic(
                    "test.suite.skipped_after_class_failure", test=test.canonical_tag
                )

            if self._cleanup:
                self._removeTestAtIndex(index)

        self._tearDownPreviousClass(None, result)
        return result

    def _handleClassSetUp(self, test: TestCase, result: OdooTestResult) -> None:
        previousClass = result._previousTestClass
        currentClass = test.__class__
        if currentClass == previousClass:
            return
        if currentClass.__unittest_skip__:
            _debug.logic(
                "test.suite.class_skipped",
                cls=currentClass.__qualname__,
                why=currentClass.__unittest_skip_why__,
            )
            return

        currentClass._classSetupFailed = False

        with _debug.perf(
            "test.suite.class_setup", cls=util.strclass(currentClass)
        ) as span:
            queries_before = db.sql_counter  # debuglog
            try:
                currentClass.setUpClass()
            except Exception as e:
                currentClass._classSetupFailed = True
                className = util.strclass(currentClass)
                self._createClassOrModuleLevelException(
                    result, e, "setUpClass", className
                )
            finally:
                span.set(
                    queries=db.sql_counter - queries_before,
                    failed=currentClass._classSetupFailed,
                )
                if currentClass._classSetupFailed is True:
                    currentClass.doClassCleanups()
                    if currentClass.tearDown_exceptions:
                        for exc in currentClass.tearDown_exceptions:
                            self._createClassOrModuleLevelException(
                                result, exc[1], "setUpClass", className, info=exc
                            )

    def _createClassOrModuleLevelException(
        self,
        result: OdooTestResult,
        exception: BaseException,
        method_name: str,
        parent: str,
        info: Any = None,
    ) -> None:
        errorName = f"{method_name} ({parent})"
        error = _ErrorHolder(errorName)
        skipped = isinstance(exception, case.SkipTest)
        _debug.lifecycle(
            "test.suite.class_error",
            hook=method_name,
            cls=parent,
            error=type(exception).__name__,
            skip=skipped,
            from_cleanup=info is not None,
        )
        if skipped:
            result.addSkip(
                error,
                str(exception),
                infrastructure=isinstance(exception, InfrastructureUnavailable),
            )
        elif not info:
            result.addError(error, sys.exc_info())
        else:
            result.addError(error, info)

    def _tearDownPreviousClass(
        self, test: TestCase | None, result: OdooTestResult
    ) -> None:
        previousClass = result._previousTestClass
        currentClass = type(test) if test is not None else None
        if currentClass == previousClass:
            return
        if not previousClass:
            return
        if previousClass._classSetupFailed:
            _debug.logic(
                "test.suite.class_teardown_skipped",
                cls=previousClass.__qualname__,
                reason="setup_failed",
            )
            return
        if previousClass.__unittest_skip__:
            return
        with _debug.perf(
            "test.suite.class_teardown", cls=util.strclass(previousClass)
        ) as span:
            queries_before = db.sql_counter  # debuglog
            try:
                previousClass.tearDownClass()
            except Exception as e:
                className = util.strclass(previousClass)
                self._createClassOrModuleLevelException(
                    result, e, "tearDownClass", className
                )
            finally:
                previousClass.doClassCleanups()
                span.set(
                    queries=db.sql_counter - queries_before,
                    cleanup_errors=len(previousClass.tearDown_exceptions),
                )
                if previousClass.tearDown_exceptions:
                    for exc in previousClass.tearDown_exceptions:
                        className = util.strclass(previousClass)
                        self._createClassOrModuleLevelException(
                            result, exc[1], "tearDownClass", className, info=exc
                        )


class _ErrorHolder:
    failureException = None

    def __init__(self, description: str) -> None:
        self.description = description

    def id(self) -> str:
        return self.description

    def shortDescription(self) -> None:
        return

    def __repr__(self) -> str:
        return f"<ErrorHolder description={self.description!r}>"

    def __str__(self) -> str:
        return self.id()

    def run(self, result: OdooTestResult) -> None:
        pass

    def __call__(self, result: OdooTestResult) -> None:
        return self.run(result)

    def countTestCases(self) -> int:
        return 0


class OdooSuite(TestSuite):
    @staticmethod
    def _timing(
        result: OdooTestResult, measured: type | None, hook: str
    ) -> AbstractContextManager:
        if (
            measured is None
            or not hasattr(result, "stats")
            or not stats_logger.isEnabledFor(logging.INFO)
        ):
            return contextlib.nullcontext()
        return result.collectStats(
            f"{measured.__module__}.{measured.__qualname__}.{hook}"
        )

    def _handleClassSetUp(self, test: TestCase, result: OdooTestResult) -> None:
        currentClass = type(test)
        entering = None
        if (
            result._previousTestClass is not currentClass
            and not currentClass.__unittest_skip__
        ):
            entering = currentClass
        with self._timing(result, entering, "setUpClass"):
            super()._handleClassSetUp(test, result)

    def _tearDownPreviousClass(
        self, test: TestCase | None, result: OdooTestResult
    ) -> None:
        previousClass = result._previousTestClass
        currentClass = type(test) if test is not None else None
        leaving = None
        if (
            previousClass
            and previousClass is not currentClass
            and not previousClass._classSetupFailed
            and not previousClass.__unittest_skip__
        ):
            leaving = previousClass
        with self._timing(result, leaving, "tearDownClass"):
            super()._tearDownPreviousClass(test, result)

    def has_http_case(self) -> bool:
        found = any(isinstance(test_case, HttpCase) for test_case in self)
        _debug.logic("test.suite.has_http_case", found=found, tests=len(self._tests))
        return found
