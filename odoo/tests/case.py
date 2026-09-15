import contextlib
import inspect
import logging
import sys
from pathlib import PurePath
from typing import TYPE_CHECKING, Any, ClassVar, ParamSpec
from unittest import SkipTest
from unittest import TestCase as _TestCase

from .. import db
from ..libs.debug_log import DebugLog
from .utils import InfrastructureUnavailable, addon_relative_path

if TYPE_CHECKING:
    import types
    from collections.abc import Callable, Generator

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


__unittest = True

_subtest_msg_sentinel = object()

_P = ParamSpec("_P")


class _Outcome:
    def __init__(self, test: TestCase, result: Any) -> None:
        self.result = result
        self.success = True
        self.test = test

    @contextlib.contextmanager
    def testPartExecutor(self, test_case: TestCase) -> Generator[None]:
        try:
            yield
        except KeyboardInterrupt:
            raise
        except SkipTest as e:
            self.success = False
            if _debug.logic.enabled:
                _debug.logic(
                    "test.case.part_skipped",
                    test=test_case.id(),
                    infrastructure=isinstance(e, InfrastructureUnavailable),
                )
            self.result.addSkip(
                test_case,
                str(e),
                infrastructure=isinstance(e, InfrastructureUnavailable),
            )
        except BaseException:
            exception_type, exception, tb = sys.exc_info()
            self.success = False
            if _debug.logic.enabled:
                _debug.logic(
                    "test.case.part_failed",
                    test=test_case.id(),
                    error=exception_type.__name__ if exception_type else None,
                    subtest=isinstance(test_case, _SubTest),
                )
            if tb is not None:
                tb = self._complete_traceback(tb)
            self.test._addError(self.result, test_case, (exception_type, exception, tb))
            del exception_type, exception, tb

    def _complete_traceback(
        self, initial_tb: types.TracebackType
    ) -> types.TracebackType | None:
        Traceback = type(initial_tb)

        tb_frames = set()
        walk: types.TracebackType | None = initial_tb
        while walk:
            tb_frames.add(walk.tb_frame)
            walk = walk.tb_next
        tb: types.TracebackType | None = initial_tb

        current_frame = inspect.currentframe()
        common_frame = None
        while current_frame:
            if current_frame in tb_frames:
                common_frame = current_frame
            current_frame = current_frame.f_back

        if not common_frame:
            _debug.logic("test.case.traceback_no_common_frame", frames=len(tb_frames))
            _logger.warning(
                "No common frame found with current stack, displaying full stack"
            )
            return initial_tb

        while tb and tb.tb_frame != common_frame:
            tb = tb.tb_next

        current_frame = common_frame.f_back
        while current_frame:
            tb = Traceback(
                tb, current_frame, current_frame.f_lasti, current_frame.f_lineno
            )
            current_frame = current_frame.f_back

        while tb:
            code = tb.tb_frame.f_code
            if PurePath(code.co_filename).name == "case.py" and code.co_name in (
                "_callTestMethod",
                "_callSetUp",
                "_callTearDown",
                "_callCleanup",
            ):
                _debug.logic("test.case.traceback_rooted", part=code.co_name)
                return tb.tb_next
            tb = tb.tb_next

        _debug.logic("test.case.traceback_no_root_frame", frames=len(tb_frames))
        _logger.warning("No root frame found, displaying full stacks")
        return initial_tb


class TestCase(_TestCase):
    _class_cleanups: ClassVar[list] = []
    tearDown_exceptions: ClassVar[list] = []
    _classSetupFailed: ClassVar[bool] = False
    __unittest_skip__ = False
    __unittest_skip_why__ = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        offenders = sorted(
            name
            for name, attr in vars(cls).items()
            if getattr(attr, "__unittest_expecting_failure__", False)
        )
        if cls.__dict__.get("__unittest_expecting_failure__"):
            offenders.append("the class itself")
        if offenders:
            raise TypeError(
                f"{cls.__module__}.{cls.__qualname__}: unittest.expectedFailure "
                f"is not supported by the Odoo test runner "
                f"({', '.join(offenders)}). Assert the failure explicitly, or "
                f"skip the test with a reason."
            )

    def __init__(self, methodName: str = "runTest") -> None:
        self._testMethodName = methodName
        self._outcome: _Outcome | None = None
        if methodName != "runTest" and not hasattr(self, methodName):
            raise ValueError(f"no such test method in {self.__class__}: {methodName}")
        self._cleanups: list = []
        self._subtest: _SubTest | None = None

        self._type_equality_funcs: dict[type, str] = {
            dict: "assertDictEqual",
            list: "assertListEqual",
            tuple: "assertTupleEqual",
            set: "assertSetEqual",
            frozenset: "assertSetEqual",
            str: "assertMultiLineEqual",
        }

    def addCleanup(
        self,
        function: Callable[_P, object],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> None:
        self._cleanups.append((function, args, kwargs))

    @classmethod
    def addClassCleanup(
        cls,
        function: Callable[_P, object],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> None:
        cls._class_cleanups.append((function, args, kwargs))

    def shortDescription(self) -> None:
        return None

    @contextlib.contextmanager
    def subTest(
        self, msg: Any = _subtest_msg_sentinel, **params: Any
    ) -> Generator[None]:
        parent = self._subtest
        if parent:
            params = {
                **params,
                **{k: v for k, v in parent.params.items() if k not in params},
            }
        subtest = self._subtest = _SubTest(self, msg, params)
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "test.case.subtest",
                test=self.id(),
                desc=subtest._subDescription(),
                nested=parent is not None,
            )
        try:
            assert self._outcome is not None
            with self._outcome.testPartExecutor(subtest):
                yield
        finally:
            self._subtest = parent

    def _addError(self, result: Any, test: TestCase, exc_info: tuple | None) -> None:
        if isinstance(test, _SubTest):
            result.addSubTest(test.test_case, test, exc_info)
        elif exc_info is not None:
            if issubclass(exc_info[0], self.failureException):
                result.addFailure(test, exc_info)
            else:
                result.addError(test, exc_info)

    def _callSetUp(self) -> None:
        self.setUp()

    def _callTestMethod(self, method: Any) -> None:
        method()

    def _callTearDown(self) -> None:
        self.tearDown()

    def _callCleanup(self, function: Any, *args: Any, **kwargs: Any) -> None:
        function(*args, **kwargs)

    def run(self, result: Any) -> Any:  # type: ignore[override]  # a result is mandatory here
        result.startTest(self)

        testMethod = getattr(self, self._testMethodName)

        skip = False
        skip_why = ""
        try:
            skip = self.__class__.__unittest_skip__ or testMethod.__unittest_skip__
            skip_why = (
                self.__class__.__unittest_skip_why__
                or testMethod.__unittest_skip_why__
                or ""
            )
        except AttributeError:
            pass
        if skip:
            if _debug.lifecycle.enabled:
                _debug.lifecycle(
                    "test.case.skipped",
                    test=self.canonical_tag,
                    level="class" if self.__class__.__unittest_skip__ else "method",
                    why=skip_why,
                )
            result.addSkip(self, skip_why)
            result.stopTest(self)
            return None

        if self.__class__.__dict__.get("__unittest_expecting_failure__") or getattr(
            testMethod, "__unittest_expecting_failure__", False
        ):
            if _debug.logic.enabled:
                _debug.logic(
                    "test.case.expected_failure_refused", test=self.canonical_tag
                )
            try:
                raise TypeError(
                    "unittest.expectedFailure is not supported by the Odoo test "
                    f"runner ({self.id()}). Assert the failure explicitly, or "
                    "skip the test with a reason."
                )
            except TypeError:
                result.addError(self, sys.exc_info())
            result.stopTest(self)
            return None

        outcome = _Outcome(self, result)
        span = _debug.perf("test.case.run", test=self.canonical_tag)
        try:
            self._outcome = outcome
            with span:
                queries_before = db.sql_counter
                with outcome.testPartExecutor(self):
                    self._callSetUp()
                span.set(setup_ok=outcome.success)
                if outcome.success:
                    with outcome.testPartExecutor(self):
                        self._callTestMethod(testMethod)
                    span.set(method_ok=outcome.success)
                    with outcome.testPartExecutor(self):
                        self._callTearDown()

                self.doCleanups()
                span.set(
                    success=outcome.success, queries=db.sql_counter - queries_before
                )
            if outcome.success:
                result.addSuccess(self)
            return result
        finally:
            result.stopTest(self)

            self._outcome = None

    def doCleanups(self) -> None:

        assert self._outcome is not None
        count = len(self._cleanups)  # debuglog
        while self._cleanups:
            function, args, kwargs = self._cleanups.pop()
            with self._outcome.testPartExecutor(self):
                self._callCleanup(function, *args, **kwargs)
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "test.case.cleanups",
                test=self.canonical_tag,
                count=count,
                success=self._outcome.success,
            )

    @classmethod
    def doClassCleanups(cls) -> None:
        cls.tearDown_exceptions = []
        count = len(cls._class_cleanups)  # debuglog
        while cls._class_cleanups:
            function, args, kwargs = cls._class_cleanups.pop()
            try:
                function(*args, **kwargs)
            except Exception as exc:
                _debug.logic(
                    "test.case.class_cleanup_failed",
                    cls=cls.__qualname__,
                    function=getattr(function, "__qualname__", repr(function)),
                    error=type(exc).__name__,
                )
                cls.tearDown_exceptions.append(sys.exc_info())
        _debug.lifecycle(
            "test.case.class_cleanups",
            cls=cls.__qualname__,
            count=count,
            errors=len(cls.tearDown_exceptions),
        )

    @property
    def canonical_tag(self) -> str:
        path = addon_relative_path(self.__module__)
        return f"{path}:{self.__class__.__name__}.{self._testMethodName}"

    def get_log_metadata(self) -> dict[str, str]:
        return {
            "canonical_tag": self.canonical_tag,
        }


class _SubTest(TestCase):
    def __init__(
        self, test_case: TestCase, message: Any, params: dict[str, Any]
    ) -> None:
        super().__init__()
        self._message = message
        self.test_case = test_case
        self.params = params
        self.failureException = test_case.failureException

    def runTest(self) -> None:
        raise NotImplementedError("subtests cannot be run directly")

    def _subDescription(self) -> str:
        parts = []
        if self._message is not _subtest_msg_sentinel:
            parts.append(f"[{self._message}]")
        if self.params:
            params_desc = ", ".join(f"{k}={v!r}" for (k, v) in self.params.items())
            parts.append(f"({params_desc})")
        return " ".join(parts) or "(<subtest>)"

    def id(self) -> str:
        return f"{self.test_case.id()} {self._subDescription()}"

    def __str__(self) -> str:
        return f"{self.test_case} {self._subDescription()}"
