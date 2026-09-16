import ast
import contextlib
import difflib
import gc
import inspect
import logging
import os
import pathlib
import re
import sys
import threading
import weakref
from contextlib import contextmanager
from functools import partial
from pathlib import PurePath
from unittest import SkipTest, skip
from unittest.mock import patch

from odoo.db import Cursor
from odoo.orm.runtime.backend import COPY_THRESHOLD
from odoo.tests import browser
from odoo.tests.benchmark import compare_results, compute_stats
from odoo.tests.case import TestCase
from odoo.tests.common import (
    BaseCase,
    HttpCase,
    TransactionCase,
    _registry_test_lock,
    mute_logger,
    release_stranded_test_cursors,
    release_test_lock,
    users,
    warmup,
)
from odoo.tests.cursor import TestCursor, _release_foreign_acquisition
from odoo.tests.form import O2MValue
from odoo.tests.result import OdooTestResult, Stat
from odoo.tests.suite import OdooSuite
from odoo.tests.tag_selector import TagsSelector
from odoo.tests.transaction_case import (
    _DELEGATING_STATEMENTS,
    _STATEMENT_RECORDERS,
    RegistryRLock,
)
from odoo.tests.utils import (
    InfrastructureUnavailable,
    addon_relative_path,
    env_int,
)

_logger = logging.getLogger(__name__)


@contextmanager
def _nested_suite_run():
    import odoo.modules.module as module_state

    outer = module_state.current_test
    try:
        yield
    finally:
        module_state.current_test = outer


class TestTestSuite(TestCase):
    test_tags = {"standard", "at_install"}
    test_module = "base"

    def test_test_suite(self):

        def get_method_additional_tags(self, method):
            return []


class TestRunnerLoggingCommon(TransactionCase):
    def setUp(self):
        self.expected_logs = None
        self.expected_first_frame_methods = None
        return super().setUp()

    def _addError(self, result, test, exc_info):
        try:
            self.test_result = result

            if exc_info:
                tb = exc_info[2]
                self._check_first_frame(tb)

            log_records = []

            def makeRecord(
                logger,
                name,
                level,
                fn,
                lno,
                msg,
                args,
                exc_info,
                func=None,
                extra=None,
                sinfo=None,
            ):
                # The odoo.debug.* channels (odoo/libs/debug_log.py) are an
                # orthogonal stream, off by default; what this pins is the
                # runner's own report lines, so they stay out of the capture.
                if name.startswith("odoo.debug."):
                    return
                log_records.append(
                    {
                        "logger": logger,
                        "name": name,
                        "level": level,
                        "fn": fn,
                        "lno": lno,
                        "msg": msg % args,
                        "exc_info": exc_info,
                        "func": func,
                        "extra": extra,
                        "sinfo": sinfo,
                    }
                )

            def handle(logger, record):
                return

            fake_result = OdooTestResult()
            with (
                patch("logging.Logger.makeRecord", makeRecord),
                patch("logging.Logger.handle", handle),
            ):
                super()._addError(fake_result, test, exc_info)

            self._check_log_records(log_records)

        except Exception:
            _logger.exception("unexpected exception in _feedErrorsToResult")

    def _check_first_frame(self, tb):
        if self.expected_first_frame_methods is None:
            expected_first_frame_method = self._testMethodName
        else:
            expected_first_frame_method = self.expected_first_frame_methods.pop(0)
        if expected_first_frame_method.endswith("_with_decorators"):
            return
        first_frame_method = tb.tb_frame.f_code.co_name
        if first_frame_method != expected_first_frame_method:
            self._log_error(
                f"Checking first tb frame: {first_frame_method} is not equal to {expected_first_frame_method}"
            )

    def _check_log_records(self, log_records):
        for log_record in log_records:
            self._assert_log_equal(log_record, "logger", _logger)
            self._assert_log_equal(
                log_record, "name", "odoo.addons.base.tests.test_test_suite"
            )
            self._assert_log_equal(log_record, "fn", __file__)
            self._assert_log_equal(log_record, "func", self._testMethodName)

        if self.expected_logs is not None:
            for log_record in log_records:
                level, msg = self.expected_logs.pop(0)
                self._assert_log_equal(log_record, "level", level)
                self._assert_log_equal(log_record, "msg", msg)

    def _assert_log_equal(self, log_record, key, expected):
        value = log_record[key]
        if key == "msg":
            value = self._clean_message(value)
        if value != expected:
            if key != "msg":
                self._log_error(
                    f"Key `{key}` => `{value}` is not equal to `{expected}` \n {log_record['msg']}"
                )
            else:
                diff = "\n".join(
                    difflib.ndiff(expected.splitlines(), value.splitlines())
                )
                self._log_error(f"Key `{key}` did not matched expected:\n{diff}")

    def _log_error(self, message):
        self.test_result.addError(self, (AssertionError, AssertionError(message), None))

    def _clean_message(self, message):
        root_path = PurePath(__file__).parents[4]
        python_path = PurePath(contextlib.__file__).parent
        message = re.sub(r"line \d+", "line $line", message)
        message = re.sub(r"py:\d+", "py:$line", message)
        message = re.sub(r"decorator-gen-\d+", "decorator-gen-xxx", message)
        message = re.sub(r"^\s*~*\^+~*\s*\n", "", message, flags=re.MULTILINE)
        message = re.sub(r"\.\.\.<\d+ lines>\.\.\.", "...<$elided>...", message)
        message = message.replace(f'"{root_path}', '"/root_path/odoo')
        message = message.replace(f'"{python_path}', '"/usr/lib/python')
        return message.replace("\\", "/")


class TestRunnerLogging(TestRunnerLoggingCommon):
    def setUp(self):
        old_level = _logger.level
        _logger.setLevel(logging.INFO)
        self.addCleanup(_logger.setLevel, old_level)
        return super().setUp()

    def test_has_add_error(self):
        self.assertTrue(hasattr(self, "_addError"))

    def test_raise(self):
        raise Exception("This is an error")

    def test_raise_subtest(self):

        def make_message(message):
            return f"""ERROR: Subtest TestRunnerLogging.test_raise_subtest (<subtest>)
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_raise_subtest
    raise Exception("{message}")
Exception: {message}
"""

        self.expected_logs = [
            (logging.INFO, "=" * 70),
            (logging.ERROR, make_message("This is an error")),
        ]
        with self.subTest():
            raise Exception("This is an error")
        self.assertFalse(self.expected_logs, "Error should have been logged immediatly")

        self.expected_logs = [
            (logging.INFO, "=" * 70),
            (logging.ERROR, make_message("This is an error2")),
        ]

        with self.subTest():
            raise Exception("This is an error2")
        self.assertFalse(self.expected_logs, "Error should have been logged immediatly")

    @users("__system__")
    @warmup
    def test_with_decorators(self):
        message = """ERROR: Subtest TestRunnerLogging.test_with_decorators (login='__system__')
Traceback (most recent call last):
  File "/root_path/odoo/odoo/tests/common.py", line $line, in with_users
    func(self, *args, **kwargs)
  File "/root_path/odoo/odoo/tests/common.py", line $line, in warmup
    func(self, *args, **kwargs)
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_with_decorators
    raise Exception("This is an error")
Exception: This is an error
"""
        self.expected_logs = [
            (logging.INFO, "=" * 70),
            (logging.ERROR, message),
        ]
        raise Exception("This is an error")

    def test_traverse_contextmanager(self):
        @contextmanager
        def assertSomething():
            yield
            raise Exception("This is an error")

        with assertSomething():
            pass

    def test_subtest_sub_call(self):
        def func():
            with self.subTest():
                raise Exception("This is an error")

        func()

    def test_call_stack(self):
        message = """ERROR: TestRunnerLogging.test_call_stack
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_call_stack
    alpha()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in alpha
    beta()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in beta
    gamma()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in gamma
    raise Exception("This is an error")
Exception: This is an error
"""
        self.expected_logs = [
            (logging.INFO, "=" * 70),
            (logging.ERROR, message),
        ]

        def alpha():
            beta()

        def beta():
            gamma()

        def gamma():
            raise Exception("This is an error")

        alpha()

    def test_call_stack_context_manager(self):
        message = """ERROR: TestRunnerLogging.test_call_stack_context_manager
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_call_stack_context_manager
    alpha()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in alpha
    beta()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in beta
    gamma()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in gamma
    raise Exception("This is an error")
Exception: This is an error
"""
        self.expected_logs = [
            (logging.INFO, "=" * 70),
            (logging.ERROR, message),
        ]

        def alpha():
            beta()

        def beta():
            with self.with_user("admin"):
                gamma()
                return 0

        def gamma():
            raise Exception("This is an error")

        alpha()

    def test_call_stack_subtest(self):
        message = """ERROR: Subtest TestRunnerLogging.test_call_stack_subtest (<subtest>)
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_call_stack_subtest
    alpha()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in alpha
    beta()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in beta
    gamma()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in gamma
    raise Exception("This is an error")
Exception: This is an error
"""
        self.expected_logs = [
            (logging.INFO, "=" * 70),
            (logging.ERROR, message),
        ]

        def alpha():
            beta()

        def beta():
            with self.subTest():
                gamma()

        def gamma():
            raise Exception("This is an error")

        alpha()

    def test_assertQueryCount(self):
        message = """FAIL: Subtest TestRunnerLogging.test_assertQueryCount (<subtest>)
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_assertQueryCount
    with self.assertQueryCount(system=0):
  File "/usr/lib/python/contextlib.py", line $line, in __exit__
    next(self.gen)
  File "/root_path/odoo/odoo/tests/transaction_case.py", line $line, in assertQueryCount
    self.fail(
        "Query count more than expected for user %s: %d > %d in %s at %s:%s"
    ...<$elided>...
        )
    )
AssertionError: Query count more than expected for user __system__: 1 > 0 in test_assertQueryCount at base/tests/test_test_suite.py:$line
"""
        self.expected_logs = [
            (logging.INFO, "=" * 70),
            (logging.ERROR, message),
        ]
        with self.assertQueryCount(system=0):
            self.env.cr.execute("SELECT 1")

    @users("__system__")
    @warmup
    def test_assertQueryCount_with_decorators(self):
        with self.assertQueryCount(system=0):
            self.env.cr.execute("SELECT 1")

    def test_reraise(self):
        message = """ERROR: TestRunnerLogging.test_reraise
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_reraise
    alpha()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in alpha
    beta()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in beta
    raise Exception("This is an error")
Exception: This is an error
"""
        self.expected_logs = [
            (logging.INFO, "=" * 70),
            (logging.ERROR, message),
        ]

        def alpha():
            try:
                beta()
            except Exception:
                raise

        def beta():
            raise Exception("This is an error")

        alpha()

    def test_handle_error(self):
        message = """ERROR: TestRunnerLogging.test_handle_error
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in alpha
    beta()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in beta
    raise Exception("This is an error")
Exception: This is an error

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_handle_error
    alpha()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in alpha
    raise Exception("This is an error2") from err
Exception: This is an error2
"""
        self.expected_logs = [
            (logging.INFO, "=" * 70),
            (logging.ERROR, message),
        ]

        def alpha():
            try:
                beta()
            except Exception as err:
                raise Exception("This is an error2") from err

        def beta():
            raise Exception("This is an error")

        alpha()


class TestRunnerLoggingSetup(TestRunnerLoggingCommon):
    def setUp(self):
        super().setUp()
        self.expected_first_frame_methods = [
            "setUp",
            "cleanupError2",
            "cleanupError",
        ]

        def cleanupError():
            raise Exception("This is a cleanup error")

        self.addCleanup(cleanupError)

        def cleanupError2():
            raise Exception("This is a second cleanup error")

        self.addCleanup(cleanupError2)

        raise Exception("This is a setup error")

    def test_raises_setup(self):
        _logger.error("This shouldn't be executed")

    def tearDown(self):
        _logger.error("This shouldn't be executed since setup failed")


class TestRunnerLoggingTeardown(TestRunnerLoggingCommon):
    def setUp(self):
        super().setUp()
        self.expected_first_frame_methods = [
            "test_raises_teardown",
            "test_raises_teardown",
            "test_raises_teardown",
            "tearDown",
            "cleanupError2",
            "cleanupError",
        ]

        def cleanupError():
            raise Exception("This is a cleanup error")

        self.addCleanup(cleanupError)

        def cleanupError2():
            raise Exception("This is a second cleanup error")

        self.addCleanup(cleanupError2)

    def tearDown(self):
        raise Exception("This is a tearDown error")

    def test_raises_teardown(self):
        with self.subTest():
            raise Exception("This is a subTest error")
        with self.subTest():
            raise Exception("This is a second subTest error")
        raise Exception("This is a test error")


class TestSubtests(BaseCase):
    def test_nested_subtests(self):
        with self.subTest(a=1, x=2):
            with self.subTest(b=3, x=4):
                self.assertEqual(self._subtest._subDescription(), "(b=3, x=4, a=1)")
            with self.subTest(b=5, x=6):
                self.assertEqual(self._subtest._subDescription(), "(b=5, x=6, a=1)")


class TestClassSetup(BaseCase):
    @classmethod
    def setUpClass(cls):
        raise SkipTest("Skip this class")

    def test_method(self):
        pass


class TestClassTeardown(BaseCase):
    @classmethod
    def tearDownClass(cls):
        raise SkipTest("Skip this class")

    def test_method(self):
        pass


class Test01ClassCleanups(BaseCase):
    executed = False
    cleanup = False

    @classmethod
    def setUpClass(cls):
        cls.executed = True

        def doCleanup():
            cls.cleanup = True

        cls.addClassCleanup(doCleanup)

    def test_dummy(self):
        pass


class Test02ClassCleanupsCheck(BaseCase):
    def test_classcleanups(self):
        self.assertTrue(
            Test01ClassCleanups.executed,
            "This test only makes sence when executed after Test01ClassCleanups",
        )
        self.assertTrue(
            Test01ClassCleanups.cleanup,
            "TestClassCleanup shoudl have been cleanuped",
        )


@skip
class TestSkipClass(BaseCase):
    def test_classcleanups(self):
        raise Exception("This should be skipped")


class TestSkipMethof(BaseCase):
    @skip
    def test_skip_method(self):
        raise Exception("This should be skipped")


class TestRegistryRLock(BaseCase):
    def test_registry_rlock_count(self):
        lock = RegistryRLock()
        for i in range(5):
            self.assertEqual(lock.count, i)
            lock.acquire()
        for i in range(5):
            self.assertEqual(lock.count, 5 - i)
            lock.release()


class TestCursorStack(TransactionCase):
    def test_out_of_order_close(self):
        lock = threading.RLock()
        cr1 = self.registry.cursor()
        cr2 = self.registry.cursor()
        tc1 = TestCursor(cr1, lock, readonly=False)
        tc2 = TestCursor(cr2, lock, readonly=False)

        def cleanup():
            for tc in (tc1, tc2):
                if not tc._closed:
                    tc.close()
            cr1.close()
            cr2.close()

        self.addCleanup(cleanup)

        with self.assertLogs("odoo.tests.cursor", level="WARNING"):
            tc1.close()
        self.assertNotIn(tc1, TestCursor._cursors_stack)
        self.assertIn(tc2, TestCursor._cursors_stack)
        self.assertFalse(tc2._closed)

        tc2.close()
        self.assertNotIn(tc2, TestCursor._cursors_stack)

    def test_readonly_nesting_enforced_lazily(self):
        lock = threading.RLock()
        cr_ro = self.registry.cursor()
        cr_rw = self.registry.cursor()
        tc_ro = TestCursor(cr_ro, lock, readonly=True)

        def cleanup():
            if not tc_ro._closed:
                tc_ro.close()
            cr_ro.close()
            cr_rw.close()

        self.addCleanup(cleanup)

        tc_rw = TestCursor(cr_rw, lock, readonly=False)
        tc_rw.close()

        tc_ro.execute("SELECT 1")
        with self.assertRaisesRegex(Exception, "read/write test cursor"):
            TestCursor(cr_rw, lock, readonly=False)
        self.assertEqual([tc_ro], TestCursor._cursors_stack)


class TestBenchmarkStats(BaseCase):
    def test_compute_stats_raw_extremes_joint_trim(self):
        times = [100.0] * 19 + [10000.0]
        db_times = [60.0] * 19 + [9990.0]
        query_counts = [3] * 19 + [50]
        stats = compute_stats("t", times, query_counts, db_times)

        self.assertEqual(stats.iterations, 20)
        self.assertEqual(stats.total_samples, 19)
        self.assertEqual(stats.min_us, 100.0)
        self.assertEqual(stats.max_us, 10000.0)
        self.assertAlmostEqual(stats.mean_us, 100.0)
        self.assertAlmostEqual(stats.db_time_us, 60.0)
        self.assertAlmostEqual(stats.db_ratio, 0.6)
        self.assertAlmostEqual(stats.query_count_mean, 3.0)
        self.assertEqual(stats.query_count_max, 50)

    def test_compute_stats_ratio_bounded(self):
        times = [100.0] * 9 + [1000.0]
        db_times = [99.0] * 9 + [999.0]
        stats = compute_stats("t", times, [1] * 10, db_times)
        self.assertLessEqual(stats.db_ratio, 1.0)
        self.assertGreaterEqual(stats.python_time_us, 0.0)

    def test_compute_stats_small_sample_untrimmed(self):
        stats = compute_stats("t", [1.0, 2.0, 3.0], [1, 1, 1], [0.5, 0.5, 0.5])
        self.assertEqual(stats.total_samples, 3)
        self.assertEqual(stats.max_us, 3.0)


class TestEnvInt(BaseCase):
    def test_env_int(self):
        var = "ODOO_TEST_ENV_INT_PROBE"
        self.assertEqual(env_int(var, 3), 3)
        for raw, expected in [("", 3), (" ", 3), ("0", 0), ("42", 42), ("-1", -1)]:
            with self.subTest(raw=raw), patch.dict(os.environ, {var: raw}):
                self.assertEqual(env_int(var, 3), expected)
        with patch.dict(os.environ, {var: "nope"}), self.assertRaises(ValueError):
            env_int(var, 3)


class TestRetryAccounting(BaseCase):
    class _Case(BaseCase):
        test_tags = {"standard"}
        test_module = "base"
        attempts = 0
        failures_wanted = 0

        def test_probe(self):
            type(self).attempts += 1
            if self.attempts <= self.failures_wanted:
                raise AssertionError("deliberate")

    def _run(self, retries, failures_wanted=0):
        case = type("Probe", (self._Case,), {})
        case.failures_wanted = failures_wanted
        case._tests_run_count = retries + 1
        result = OdooTestResult()
        with mute_logger(__name__):
            case("test_probe").run(result)
        return case.attempts, result

    def test_passing_test_is_counted_once_with_retries(self):
        for retries in (0, 1, 3):
            with self.subTest(retries=retries):
                attempts, result = self._run(retries)
                self.assertEqual(attempts, 1)
                self.assertEqual(result.testsRun, 1)
                self.assertTrue(result.wasSuccessful())

    def test_flaky_test_is_counted_once(self):
        attempts, result = self._run(retries=2, failures_wanted=2)
        self.assertEqual(attempts, 3, "should have retried twice")
        self.assertEqual(result.testsRun, 1)
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(result.failures_count, 0, "soft failures must not count")

    def test_always_failing_test_is_counted_once_and_fails(self):
        attempts, result = self._run(retries=1, failures_wanted=99)
        self.assertEqual(attempts, 2)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.failures_count, 1)


class TestPatchExecuteStatementApi(TransactionCase):
    @staticmethod
    def _marks_a_statement(name):
        attr = getattr(Cursor, name, None)
        if not callable(attr):
            return False
        code = getattr(inspect.unwrap(attr), "__code__", None)
        return code is not None and "_before_statement" in code.co_names

    def test_every_marked_entry_point_is_recorded(self):
        marked = {name for name in dir(Cursor) if self._marks_a_statement(name)}
        self.assertTrue(marked, "Cursor marks no statement entry points at all")
        self.assertEqual(
            sorted(marked),
            sorted(set(_STATEMENT_RECORDERS) | _DELEGATING_STATEMENTS),
            "every statement entry point must either be recorded or be known "
            "to reach the server through execute()",
        )

    def _capture(self, func):
        self.warm = False
        with self.assertQueries([], flush=False) as caught:
            func()
        self.warm = True
        return list(caught)

    def test_executemany_is_recorded_once(self):
        caught = self._capture(
            lambda: self.cr.executemany("SELECT %s::int", [(1,), (2,), (3,)])
        )
        self.assertEqual(caught, ["SELECT %s::int"])

    def test_execute_values_is_recorded_once_via_execute(self):
        self.cr.execute("CREATE TEMP TABLE _probe_ev (n int)")
        caught = self._capture(
            lambda: self.cr.execute_values(
                "INSERT INTO _probe_ev (n) VALUES %s", [(1,), (2,)]
            )
        )
        self.assertEqual(caught, ["INSERT INTO _probe_ev (n) VALUES (%s), (%s)"])

    def test_copy_from_is_recorded_as_a_copy(self):
        self.cr.execute("CREATE TEMP TABLE _probe_cp (a int, b text)")
        caught = self._capture(
            lambda: self.cr.copy_from("_probe_cp", ["a", "b"], [(1, "x"), (2, "y")])
        )
        self.assertEqual(caught, ['COPY "_probe_cp" ("a", "b") FROM STDIN'])

    def _bulk_create(self):
        self.env["res.partner"].create(
            [{"name": f"probe {i}"} for i in range(COPY_THRESHOLD + 2)]
        )
        self.env.flush_all()

    def test_bulk_create_write_is_visible(self):
        caught = self._capture(self._bulk_create)
        self.assertTrue(
            any(q.startswith('COPY "res_partner"') for q in caught),
            f"the COPY that inserted the rows is missing from {caught}",
        )

    def test_captured_queries_are_always_strings(self):
        caught = self._capture(self._bulk_create)
        self.assertTrue(caught)
        for query in caught:
            self.assertIsInstance(query, str)
        self._normalize_query(caught[0])
        "\n".join(caught)


class TestReadonlyModeIsTestScoped(TransactionCase):
    def test_a_disables_readonly(self):
        self.registry_enter_test_mode(register_cleanup=True)
        self.set_registry_readonly_mode(False)
        self.assertFalse(type(self)._registry_readonly_enabled)

    def test_b_sees_the_default_again(self):
        self.assertTrue(
            type(self)._registry_readonly_enabled,
            "readonly enforcement leaked out of the previous test",
        )


class Test03LeakPatchers(BaseCase):
    class Target:
        a = 1
        b = 2
        c = 3

    def test_leak_three_patchers(self):
        for name, value in (("a", 10), ("b", 20), ("c", 30)):
            patch.object(self.Target, name, value).start()


class Test04LeakedPatchersCheck(BaseCase):
    def test_every_leaked_patcher_was_stopped(self):
        target = Test03LeakPatchers.Target
        self.addCleanup(setattr, target, "a", 1)
        self.addCleanup(setattr, target, "b", 2)
        self.addCleanup(setattr, target, "c", 3)
        self.assertEqual(
            (target.a, target.b, target.c),
            (1, 2, 3),
            "patchers leaked by the previous class survived its cleanup",
        )


class TestCompleteTraceback(BaseCase):
    def test_detached_traceback_falls_back_to_the_full_stack(self):
        from odoo.tests.case import _Outcome

        captured = {}

        def in_another_thread():
            try:
                raise RuntimeError("detached")
            except RuntimeError:
                captured["tb"] = sys.exc_info()[2]

        thread = threading.Thread(target=in_another_thread)
        thread.start()
        thread.join()

        outcome = _Outcome(self, OdooTestResult())
        with self.assertLogs("odoo.tests.case", "WARNING"):
            result = outcome._complete_traceback(captured["tb"])
        self.assertIs(result, captured["tb"])


class TestBaseCaseDefaults(BaseCase):
    def test_subclass_outside_addons_is_constructible(self):
        outside = type(
            "Outside",
            (BaseCase,),
            {"__module__": "some.third.party", "test_x": lambda self: None},
        )
        self.assertIsNone(outside.test_tags, "the class keeps the sentinel")
        case = outside("test_x")
        self.assertEqual(case.test_tags, set(), "the instance gets a usable set")
        self.assertEqual(case.test_module, "")

    def test_framework_bases_keep_the_untagged_sentinel(self):
        for base in (BaseCase, TransactionCase, HttpCase):
            with self.subTest(base=base.__name__):
                self.assertIsNone(
                    base.test_tags,
                    "consuming the sentinel drops every addon subclass "
                    "of this base out of test selection",
                )


class TestSuiteReleasesFinishedTests(BaseCase):
    def test_finished_tests_are_released(self):
        holder = []

        class Probe(BaseCase):
            __module__ = "some.third.party"
            test_tags = {"standard", "at_install"}

            def test_a(self):
                holder.append(weakref.ref(self))

            def test_b(self):
                holder.append(weakref.ref(self))

        suite = OdooSuite([Probe("test_a"), Probe("test_b")])
        with _nested_suite_run():
            suite.run(OdooTestResult())

        gc.collect()
        alive = [ref for ref in holder if ref() is not None]
        self.assertEqual(len(holder), 2, "both probes ran")
        self.assertFalse(
            alive, "the suite is still holding %d finished test(s)" % len(alive)
        )


class TestStrandedTestCursorReleasesItsLock(TransactionCase):
    def test_stranded_cursor_does_not_leak_an_acquisition(self):
        before = _registry_test_lock.count

        self.registry_enter_test_mode(register_cleanup=True)
        cursor = self.registry.cursor()
        self.assertIsInstance(cursor, TestCursor)
        self.assertEqual(
            _registry_test_lock.count, before + 1, "opening one takes the lock"
        )
        self.assertIn(cursor, TestCursor._cursors_stack)

        with mute_logger("odoo.tests.transaction_case"):
            stranded = release_stranded_test_cursors("the test above")

        self.assertEqual(stranded, 1)
        self.assertEqual(TestCursor._cursors_stack, [])
        self.assertTrue(cursor._closed)
        self.assertEqual(
            _registry_test_lock.count,
            before,
            "a stranded TestCursor leaked a registry-lock acquisition; every "
            "later HttpCase request would stall for test_cursor_lock_timeout",
        )

    def test_handover_to_another_thread_still_works(self):
        acquired = []

        def worker():
            got = _registry_test_lock.acquire(timeout=5)
            acquired.append(got)
            if got:
                _registry_test_lock.release()

        with release_test_lock():
            thread = threading.Thread(target=worker)
            thread.start()
            thread.join(10)

        self.assertEqual(
            acquired, [True], "an HTTP worker thread could not take the lock"
        )

    def test_a_clean_stack_releases_nothing(self):
        before = _registry_test_lock.count
        self.assertEqual(release_stranded_test_cursors(), 0)
        self.assertEqual(_registry_test_lock.count, before)


class TestAStrandedCursorIsRecoverableAcrossThreads(BaseCase):
    def test_an_acquisition_made_by_another_thread_can_be_released(self):
        lock = RegistryRLock()
        taken = threading.Event()

        def worker():
            lock.acquire()
            taken.set()

        thread = threading.Thread(target=worker)
        thread.start()
        self.assertTrue(taken.wait(5), "the worker never took the lock")
        thread.join(5)

        _release_foreign_acquisition(lock)

        self.assertTrue(
            lock.acquire(timeout=5),
            "a TestCursor stranded by an HTTP worker holds an acquisition that "
            "thread will never return, and RLock.release() refuses from any "
            "other thread -- so the recovery path has to adopt it first, or it "
            "raises in exactly the case it exists for",
        )
        lock.release()

    def test_it_still_releases_normally_when_this_thread_owns_it(self):
        lock = RegistryRLock()
        lock.acquire()
        _release_foreign_acquisition(lock)
        self.assertTrue(lock.acquire(timeout=5))
        lock.release()

    def test_a_lock_it_cannot_adopt_is_reported_not_raised(self):
        lock = threading.RLock()
        taken = threading.Event()

        def worker():
            lock.acquire()
            taken.set()

        thread = threading.Thread(target=worker)
        thread.start()
        self.assertTrue(taken.wait(5))
        thread.join(5)

        with self.assertLogs("odoo.tests.cursor", "WARNING") as logged:
            _release_foreign_acquisition(lock)
        self.assertIn(
            "exposes no owner to adopt",
            "\n".join(logged.output),
            "the C _thread.RLock cannot be adopted, and re-raising there would "
            "reproduce the very message this path exists to avoid",
        )


class TestALeakedRequestThreadIsLoud(HttpCase):
    @contextmanager
    def _a_leaked_request_thread(self):
        stop = threading.Event()
        thread = threading.Thread(
            target=stop.wait, name="odoo.service.http.request.leaked"
        )
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join(5)

    def test_a_request_that_outlives_its_test_raises(self):
        with self._a_leaked_request_thread():
            with self.assertRaises(AssertionError) as caught:
                self._wait_remaining_requests(timeout=1)
        self.assertIn(
            "still running",
            str(caught.exception),
            "a leaked request used to be logged at INFO and the run carried on; "
            "it can still hold the registry lock through its TestCursor",
        )

    def test_it_only_warns_when_the_test_is_already_failing(self):
        with self._a_leaked_request_thread():
            with self.assertLogs(self._logger, "WARNING") as logged:
                self._wait_remaining_requests(timeout=1, strict=False)
        self.assertIn("still running", "\n".join(logged.output))

    def test_it_says_nothing_when_no_request_is_left(self):
        with self.assertNoLogs(self._logger, "WARNING"):
            self._wait_remaining_requests(timeout=1)


class TestReleaseTestLockIsSymmetric(TransactionCase):
    def test_a_thread_that_does_not_hold_it_touches_nothing(self):
        raised = []
        counts = []

        def worker():
            try:
                with release_test_lock():
                    counts.append(_registry_test_lock.count)
            except BaseException as exc:
                raised.append(exc)

        before = _registry_test_lock.count
        thread = threading.Thread(target=worker)
        with mute_logger("odoo.tests.transaction_case"):
            thread.start()
            thread.join(10)

        self.assertEqual(
            raised,
            [],
            "release_test_lock released a lock the calling thread does not "
            "own; RLock.release() raises for a non-owner, and that RuntimeError "
            "surfaces as a failure of whatever test was making the request",
        )
        self.assertEqual(
            counts,
            [before],
            "a thread that never held the lock must not hand it over",
        )
        self.assertEqual(
            _registry_test_lock.count,
            before,
            "and it must not acquire one on the way out either -- an "
            "unbalanced re-acquisition is what leaves count > 1",
        )

    def test_the_owner_still_hands_it_over_and_takes_it_back(self):
        before = _registry_test_lock.count
        with release_test_lock():
            self.assertEqual(
                _registry_test_lock.count, before - 1, "the hand-over must release"
            )
        self.assertEqual(_registry_test_lock.count, before)


class TestBrowserIsStoppedBeforeTheLockIsTakenBack(BaseCase):
    def test_the_last_registered_stop_runs_before_the_drain(self):
        lines = inspect.getsource(HttpCase.browser_js).splitlines()
        stops = [
            i for i, line in enumerate(lines) if "atexit.callback(browser.stop)" in line
        ]
        drain = next(
            i
            for i, line in enumerate(lines)
            if "self._wait_for_requests_unless_already_failing" in line
        )
        self.assertEqual(
            len(stops),
            1,
            "browser.stop is registered once, after the drain, so it runs "
            "first; a second registration would stop the browser twice",
        )
        self.assertGreater(
            stops[0],
            drain,
            "an ExitStack unwinds last-registered-first, so stopping the "
            "browser must be registered AFTER the drain to run BEFORE it -- "
            "otherwise the browser is still live while allow_requests waits "
            "60s to take the registry lock back, and a late request holding a "
            "TestCursor makes that wait time out",
        )


class TestSetUpIsRerunPerAttempt(BaseCase):
    def test_http_case_logger_is_derived_from_the_class(self):
        source = inspect.getsource(HttpCase.setUp)
        self.assertIn(
            "type(self)._logger.getChild",
            source,
            "HttpCase.setUp must derive its logger from the class attribute; "
            "self._logger.getChild(...) grows the name on every retry",
        )

    def test_repeated_setup_is_stable(self):
        names = []

        class Probe(HttpCase):
            __module__ = "some.third.party"
            _logger = logging.getLogger("probe.Class")

            def setUp(self):
                self._logger = type(self)._logger.getChild(self._testMethodName)
                names.append(self._logger.name)

            def test_x(self):
                pass

        probe = Probe("test_x")
        probe.setUp()
        probe.setUp()
        probe.setUp()
        self.assertEqual(
            names,
            ["probe.Class.test_x"] * 3,
            "setUp is not idempotent across retries",
        )


class TestOpenerCleanupIsLateBound(BaseCase):
    def test_cleanup_closes_the_current_opener(self):
        closed = []

        class FakeOpener:
            def __init__(self, name):
                self.name = name

            def close(self):
                closed.append(self.name)

        holder = type("H", (), {})()
        holder.opener = FakeOpener("first")
        cleanup = partial(HttpCase._close_opener, holder)
        holder.opener = FakeOpener("second")
        cleanup()

        self.assertEqual(
            closed,
            ["second"],
            "the cleanup closed the opener bound at setUp, leaving the one "
            "authenticate() installed open",
        )


class TestResultStatsAreSummed(BaseCase):
    def test_update_sums_colliding_ids(self):
        first, second = OdooTestResult(), OdooTestResult()
        first.stats["mod.Class.setUpClass"] = Stat(time=1.0, queries=10)
        second.stats["mod.Class.setUpClass"] = Stat(time=2.0, queries=20)
        first.update(second)
        merged = first.stats["mod.Class.setUpClass"]
        self.assertEqual(
            (merged.time, merged.queries),
            (3.0, 30),
            "colliding stat ids must sum, as collectStats does, not overwrite",
        )


class TestEveryStatementApiIsWrapped(BaseCase):
    def test_testcursor_wraps_every_recorded_statement(self):
        recorded = set(_STATEMENT_RECORDERS) | set(_DELEGATING_STATEMENTS)
        wrapped = {name for name in recorded if name in vars(TestCursor)}
        self.assertEqual(
            recorded - wrapped,
            set(),
            "these statement APIs reach the cursor via __getattr__, skipping "
            "_check_savepoint: %s" % sorted(recorded - wrapped),
        )


class TestX2MValueIndexing(BaseCase):
    def test_index_tracks_mutation(self):
        value = O2MValue({"id": i} for i in (1, 2, 3))
        self.assertEqual([value[i] for i in range(3)], [1, 2, 3])
        value.remove(2)
        self.assertEqual([value[i] for i in range(2)], [1, 3], "cache went stale")
        value.add(4, {"id": 4})
        self.assertEqual([value[i] for i in range(3)], [1, 3, 4], "cache went stale")
        value.clear()
        self.assertEqual(len(value), 0)
        value.create({"id": False})
        self.assertEqual(len(value), 1, "create must invalidate the key cache")


class TestBenchmarkStatsDerivations(BaseCase):
    def test_ms_accessors_derive_from_us(self):
        stats = compute_stats(
            "probe",
            [100.0, 120.0, 110.0, 130.0],
            [3, 3, 4, 3],
            [40.0, 50.0, 45.0, 55.0],
        )
        for field in ("mean", "median", "min", "max", "p95", "p99", "db_time"):
            with self.subTest(field=field):
                self.assertAlmostEqual(
                    getattr(stats, f"{field}_ms"), getattr(stats, f"{field}_us") / 1000
                )
        with self.assertRaises(AttributeError):
            stats.not_a_field_ms
        with self.assertRaises(AttributeError):
            stats.not_a_field

    def test_to_dict_carries_the_key_compare_results_reads(self):
        stats = compute_stats("probe", [100.0, 120.0], [1, 1], [10.0, 10.0])
        as_dict = stats.to_dict()
        self.assertEqual(as_dict["p50_us"], as_dict["median_us"])
        rendered = compare_results([as_dict], [as_dict])
        self.assertNotIn("inf", rendered)
        self.assertIn("1.00x", rendered)

    def test_both_summary_scales_render(self):
        stats = compute_stats("probe", [100.0, 120.0], [1, 1], [10.0, 10.0])
        for unit in ("us", "ms", "auto"):
            with self.subTest(unit=unit):
                self.assertIn("probe", stats.summary(unit))


class TestAddonRelativePath(BaseCase):
    def test_prefixes(self):
        self.assertEqual(
            addon_relative_path("odoo.addons.base.tests.test_x"),
            "/base/tests/test_x.py",
        )
        self.assertEqual(
            addon_relative_path("odoo.upgrade.base.tests.test_y"),
            "/base/tests/test_y.py",
        )

    def test_canonical_tag_and_tag_selector_agree(self):
        selector = TagsSelector("/base/tests/test_test_suite.py")
        self.assertTrue(selector.selects(self))
        self.assertTrue(
            self.canonical_tag.startswith("/base/tests/test_test_suite.py:")
        )


class TestInfrastructureUnavailable(BaseCase):
    def test_it_remains_compatible_with_the_unittest_skip_protocol(self):
        self.assertTrue(issubclass(InfrastructureUnavailable, SkipTest))

    def test_counted_apart_from_a_deliberate_skip(self):
        result = OdooTestResult()
        with mute_logger("odoo.addons.base.tests.test_test_suite"):
            result.addSkip(self, "not applicable here")
            result.addSkip(self, "no chrome", infrastructure=True)
        self.assertEqual(result.skipped, 2)
        self.assertEqual(result.infrastructure_skipped, 1)

    def test_the_summary_says_so(self):
        result = OdooTestResult()
        with mute_logger("odoo.addons.base.tests.test_test_suite"):
            result.addSkip(self, "no chrome", infrastructure=True)
        self.assertIn("environment could not run", str(result))

        clean = OdooTestResult()
        self.assertNotIn("environment could not run", str(clean))

    def test_update_carries_the_count(self):
        first, second = OdooTestResult(), OdooTestResult()
        with mute_logger("odoo.addons.base.tests.test_test_suite"):
            second.addSkip(self, "no chrome", infrastructure=True)
        first.update(second)
        self.assertEqual(first.infrastructure_skipped, 1)

    def test_require_infra_promotes_it_to_an_error(self):
        result = OdooTestResult()
        with (
            patch("odoo.tests.result.REQUIRE_INFRA", True),
            mute_logger("odoo.addons.base.tests.test_test_suite"),
        ):
            result.addSkip(self, "no chrome", infrastructure=True)
        self.assertEqual(result.errors_count, 1)
        self.assertFalse(
            result.wasSuccessful(),
            "with ODOO_REQUIRE_INFRA=1 a suite that could not run must not pass",
        )

    def test_browser_raises_it_rather_than_a_bare_skip(self):
        source = inspect.getsource(browser)
        self.assertNotIn(
            "unittest.SkipTest(",
            source,
            "every environment failure in browser.py must raise "
            "InfrastructureUnavailable so it can be counted and reported",
        )


class TestReporterSurvivesAFilelessTestClass(BaseCase):
    @staticmethod
    def _fileless(name, body):
        return type(
            name,
            (BaseCase,),
            {
                "__module__": "some.third.party",
                "test_tags": {"standard", "at_install"},
                "test_module": "base",
                "test_x": body,
            },
        )

    def test_a_failure_is_reported_and_the_suite_continues(self):
        ran = []
        Failing = self._fileless("Failing", lambda self: self.fail("boom"))
        Later = self._fileless("Later", lambda self: ran.append("later"))

        result = OdooTestResult()
        with _nested_suite_run(), mute_logger("some.third.party"):
            OdooSuite([Failing("test_x"), Later("test_x")]).run(result)

        self.assertEqual(
            result.failures_count, 1, "the real failure was never recorded"
        )
        self.assertEqual(
            ran, ["later"], "a crash in the reporter swallowed the rest of the suite"
        )


class TestStrandedCursorsUnwindInnermostFirst(TransactionCase):
    def test_two_stranded_cursors_leave_the_transaction_usable(self):
        from psycopg.pq import TransactionStatus

        self.registry_enter_test_mode(register_cleanup=True)
        outer = self.registry.cursor()
        outer.execute("SELECT 1")
        inner = self.registry.cursor()
        inner.execute("SELECT 1")
        self.assertIsNotNone(outer._savepoint, "outer never opened a savepoint")
        self.assertIsNotNone(inner._savepoint, "inner never opened a savepoint")

        with mute_logger("odoo.tests.transaction_case"):
            self.assertEqual(release_stranded_test_cursors("the test above"), 2)

        self.assertNotEqual(
            self.cr.connection.info.transaction_status,
            TransactionStatus.INERROR,
            "releasing the outer savepoint first destroyed the inner one, and "
            "the failed ROLLBACK TO aborted the class transaction",
        )
        self.cr.execute("SELECT 1")


class TestChildProcessGuardAgreesWithPsutil(BaseCase):
    def test_the_guard_matches_psutil_in_every_state(self):
        import subprocess
        import time

        import psutil

        from odoo.tests.transaction_case import _has_child_processes

        def descendants():
            return len(psutil.Process().children(recursive=True))

        self.assertFalse(_has_child_processes(), "started with a child process")
        self.assertEqual(descendants(), 0)

        child = subprocess.Popen(["sleep", "30"])
        grandparent = subprocess.Popen(["bash", "-c", "sleep 30 & wait"])
        try:
            time.sleep(0.2)
            self.assertTrue(descendants() >= 2, "the fixture spawned nothing")
            self.assertTrue(
                _has_child_processes(),
                "the guard would skip the walk while descendants are alive",
            )
        finally:
            child.kill()
            grandparent.kill()
            child.wait()
            grandparent.wait()

        time.sleep(0.2)
        self.assertEqual(descendants(), 0)
        self.assertFalse(_has_child_processes())


class TestTagSelectorCheckIsPure(BaseCase):
    class _Probe(BaseCase):
        test_tags = {"standard", "at_install"}
        test_module = "base"

        def test_x(self):
            pass

    def _probe(self):
        probe = self._Probe("test_x")
        probe._test_params = ["sentinel"]
        return probe

    def test_check_does_not_write_to_the_test(self):
        probe = self._probe()
        self.assertTrue(TagsSelector("standard[someparam]").selects(probe))
        self.assertEqual(
            probe._test_params,
            ["sentinel"],
            "check() must not touch _test_params",
        )

    def test_params_survive_either_evaluation_order(self):
        position = TagsSelector("at_install")
        config = TagsSelector("standard[someparam]")
        expected = [("+", "someparam")]

        for first, second in ((position, config), (config, position)):
            probe = self._probe()
            self.assertTrue(first.selects(probe) and second.selects(probe))
            config.select_params(probe)
            self.assertEqual(
                probe._test_params,
                expected,
                "the parameters depend on the order the selectors are checked",
            )

    def test_an_untagged_test_selects_no_parameters(self):
        probe = self._probe()
        probe.test_tags = set()
        self.assertEqual(TagsSelector("standard[someparam]").select_params(probe), [])


class TestFilestoreIsSweptOncePerSuite(BaseCase):
    def test_no_class_cleanup_sweeps_the_filestore(self):
        source = inspect.getsource(TransactionCase.setUpClass)
        self.assertNotIn(
            "_gc_filestore",
            source,
            "the filestore sweep is back on the per-class cleanup path",
        )

    def test_run_suite_sweeps_once(self):
        from odoo.tests import loader

        self.assertIn(
            "gc_test_filestore()",
            inspect.getsource(loader.run_suite),
            "nothing sweeps the filestore any more",
        )


class TestCommonHasNoImportEdgeToHttp(BaseCase):
    @staticmethod
    def _runtime_imports_of_http():
        from odoo.tests import common as common_module

        source = pathlib.Path(common_module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)

        def is_type_checking_guard(node):
            return isinstance(node, ast.If) and (
                getattr(node.test, "id", None) == "TYPE_CHECKING"
            )

        return [
            sub.lineno
            for node in tree.body
            if not is_type_checking_guard(node)
            for sub in ast.walk(node)
            if isinstance(sub, ast.ImportFrom) and sub.module == "http"
        ]

    def test_common_does_not_import_http_while_executing(self):
        self.assertEqual(
            self._runtime_imports_of_http(),
            [],
            "common.py imports http at module scope again; that is the cycle, "
            "and the bottom-of-file placement that resolves it is what makes "
            "http.py's imports order-dependent",
        )

    def test_every_deferred_name_resolves_to_the_http_one(self):
        from odoo.tests import common as common_module
        from odoo.tests import http as http_module

        self.assertTrue(common_module._HTTP_EXPORTS, "nothing is being deferred")
        for name in common_module._HTTP_EXPORTS:
            self.assertIs(
                getattr(common_module, name),
                getattr(http_module, name),
                f"common.{name} is not http.{name}",
            )

    def test_the_deferred_names_are_published(self):
        from odoo.tests import common as common_module

        missing = sorted(set(common_module._HTTP_EXPORTS) - set(common_module.__all__))
        self.assertEqual(
            missing,
            [],
            "a deferred name outside __all__ will not survive `from odoo.tests "
            "import *`, which is how the package re-exports it",
        )

    def test_an_unknown_attribute_still_raises(self):
        from odoo.tests import common as common_module

        with self.assertRaises(AttributeError):
            common_module.NotAThingThatExists
