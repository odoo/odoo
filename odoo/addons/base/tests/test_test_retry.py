import logging
from unittest.mock import patch

from odoo.tests import BaseCase, TransactionCase, tagged
from odoo.tests.common import _logger as test_logger

_logger = logging.getLogger(__name__)


class TestRetryCommon(BaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        original_runbot = test_logger.runbot
        # lower 25 to info to avoid spaming builds with test logs

        def runbot(message, *args):
            if message.startswith("Retrying"):
                return test_logger.info(message, *args)
            return original_runbot(message, *args)

        patcher = patch.object(test_logger, "runbot", runbot)
        cls.startClassPatcher(patcher)

    def get_tests_run_count(self):
        return BaseCase._tests_run_count

    def update_count(self):
        self.count = getattr(self, "count", 0) + 1


@tagged("test_retry", "test_retry_success")
class TestRetry(TestRetryCommon):
    """Check some tests behaviour when ODOO_TEST_FAILURE_RETRIES is set"""

    def test_log_levels(self):
        _logger.debug("test debug")
        _logger.info("test info")

    def test_retry_success(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            _logger.error("Failure")
        self.assertEqual(tests_run_count, self.count)


@tagged("test_retry", "test_retry_success")
class TestRetryTraceback(TestRetryCommon):
    """Check some tests behaviour when ODOO_TEST_FAILURE_RETRIES is set"""

    def test_retry_traceback_success(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            _logger.error("Traceback (most recent call last):\n")
        self.assertEqual(tests_run_count, self.count)


@tagged("test_retry", "test_retry_success")
class TestRetryTracebackArg(TestRetryCommon):
    def test_retry_traceback_args_success(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            _logger.error("%s", "Traceback (most recent call last):\n")
        self.assertEqual(tests_run_count, self.count)


@tagged("-standard", "test_retry", "test_retry_failures")
class TestRetryFailures(TestRetryCommon):
    def test_retry_failure_assert(self):
        self.assertFalse(True)  # intentionally always-false assertion

    def test_retry_failure_log(self):
        _logger.error("Failure")


@tagged("test_retry", "test_retry_success")
class TestRetryRollbackedCursor(TestRetryCommon, TransactionCase):
    def test_broken_cursor(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            self.env.cr.rollback()


@tagged("test_retry", "test_retry_success")
class TestRetryCommitedCursor(TestRetryCommon, TransactionCase):
    def test_broken_cursor(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            self.env.cr.commit()


@tagged("test_retry", "test_retry_success")
class TestRetryRollbackedCursorError(TestRetryCommon, TransactionCase):
    def test_broken_cursor(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            self.env.cr.rollback()
            msg = "a"
            raise Exception(msg)


@tagged("test_retry", "test_retry_success")
class TestRetryCommitedCursorError(TestRetryCommon, TransactionCase):
    def test_broken_cursor(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            self.env.cr.commit()
            msg = "a"
            raise Exception(msg)


@tagged("test_retry", "test_retry_success")
class TestRetrySubtest(TestRetryCommon):
    def test_retry_subtest_success_one(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        for i in range(3):
            if i == 1:
                with self.subTest():
                    if tests_run_count != self.count:
                        _logger.error("Failure")
                    self.assertEqual(tests_run_count, self.count)

    def test_retry_subtest_success_all(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        for _ in range(3):
            with self.subTest():
                if tests_run_count != self.count:
                    _logger.error("Failure")
                self.assertEqual(tests_run_count, self.count)


@tagged("-standard", "test_retry", "test_retry_failures")
class TestRetrySubtestFailures(TestRetryCommon):
    def test_retry_subtest_failure_one(self):
        for i in range(3):
            if i == 1:
                with self.subTest():
                    _logger.error("Failure")
                    self.assertFalse(True)  # intentionally always-false assertion

    def test_retry_subtest_failure_all(self):
        for _ in range(3):
            with self.subTest():
                _logger.error("Failure")
                self.assertFalse(True)  # intentionally always-false assertion


@tagged("-standard", "test_retry", "test_retry_disable")
class TestRetry1Disable(TestRetryCommon):
    def test_retry_0_retry_success(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            msg = "Should success on retry"
            raise Exception(msg)

    def test_retry_1_fails(self):
        msg = "Should fail twice"
        raise Exception(msg)

    def test_retry_2_fails(self):
        msg = "Should fail without retry 1"
        raise Exception(msg)

    def test_retry_3_fails(self):
        msg = "Should fail without retry 2"
        raise Exception(msg)


@tagged("-standard", "test_retry", "test_retry_disable")
class TestRetry2Disable(TestRetryCommon):
    def test_retry_second_class_fails(self):
        msg = "Should fail without retry other class"
        raise Exception(msg)
