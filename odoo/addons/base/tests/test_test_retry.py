# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import BaseCase, TransactionCase, tagged, BaseCase
from odoo.tests.common import _logger as test_logger

import logging
import os

from unittest.mock import patch

_logger = logging.getLogger(__name__)


class TestRetryCommon(BaseCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        original_runbot = test_logger.runbot
        # lower 25 to info to avoid spaming builds with test logs

        def runbot(message, *args):
            if message.startswith('Retrying'):
                return test_logger.info(message, *args)
            return original_runbot(message, *args)
        patcher = patch.object(test_logger, 'runbot', runbot)
        cls.startClassPatcher(patcher)

    def get_tests_run_count(self):
        return BaseCase._tests_run_count

    def update_count(self):
        self.count = getattr(self, 'count', 0) + 1


@tagged('test_retry', 'test_retry_success')
class TestRetry(TestRetryCommon):
    """ Check some tests behaviour when ODOO_TEST_FAILURE_RETRIES is set"""

    def test_log_levels(self):
        _logger.debug('test debug')
        _logger.info('test info')

    def test_retry_success(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            _logger.error('Failure')
        self.assertEqual(tests_run_count, self.count)


@tagged('test_retry', 'test_retry_success')
class TestRetryTraceback(TestRetryCommon):
    """ Check some tests behaviour when ODOO_TEST_FAILURE_RETRIES is set"""

    def test_retry_traceback_success(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            _logger.error('Traceback (most recent call last):\n')
        self.assertEqual(tests_run_count, self.count)


@tagged('test_retry', 'test_retry_success')
class TestRetryTracebackArg(TestRetryCommon):
    def test_retry_traceback_args_success(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            _logger.error('%s', 'Traceback (most recent call last):\n')
        self.assertEqual(tests_run_count, self.count)


@tagged('-standard', 'test_retry', 'test_retry_failures')
class TestRetryFailures(TestRetryCommon):
    def test_retry_failure_assert(self):
        self.assertFalse(1 == 1)

    def test_retry_failure_log(self):
        _logger.error('Failure')


@tagged('test_retry', 'test_retry_success')
class TestRetryRollbackedCursor(TestRetryCommon, TransactionCase):
    def test_broken_cursor(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            self.env.cr.rollback()


@tagged('test_retry', 'test_retry_success')
class TestRetryCommitedCursor(TestRetryCommon, TransactionCase):
    def test_broken_cursor(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            self.env.cr.commit()


@tagged('test_retry', 'test_retry_success')
class TestRetryRollbackedCursorError(TestRetryCommon, TransactionCase):
    def test_broken_cursor(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            self.env.cr.rollback()
            raise Exception('a')


@tagged('test_retry', 'test_retry_success')
class TestRetryCommitedCursorError(TestRetryCommon, TransactionCase):
    def test_broken_cursor(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            self.env.cr.commit()
            raise Exception('a')


@tagged('test_retry', 'test_retry_success')
class TestRetrySubtest(TestRetryCommon):

    def test_retry_subtest_success_one(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        for i in range(3):
            if i == 1:
                with self.subTest():
                    if tests_run_count != self.count:
                        _logger.error('Failure')
                    self.assertEqual(tests_run_count, self.count)

    def test_retry_subtest_success_all(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        for _ in range(3):
            with self.subTest():
                if tests_run_count != self.count:
                    _logger.error('Failure')
                self.assertEqual(tests_run_count, self.count)


@tagged('-standard', 'test_retry', 'test_retry_failures')
class TestRetrySubtestFailures(TestRetryCommon):

    def test_retry_subtest_failure_one(self):
        for i in range(3):
            if i == 1:
                with self.subTest():
                    _logger.error('Failure')
                    self.assertFalse(1 == 1)

    def test_retry_subtest_failure_all(self):
        for _ in range(3):
            with self.subTest():
                _logger.error('Failure')
                self.assertFalse(1 == 1)


@tagged('-standard', 'test_retry', 'test_retry_disable')
class TestRetry1Disable(TestRetryCommon):

    def test_retry_0_retry_success(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            raise Exception('Should success on retry')

    def test_retry_1_fails(self):
        raise Exception('Should fail twice')

    def test_retry_2_fails(self):
        raise Exception('Should fail without retry 1')

    def test_retry_3_fails(self):
        raise Exception('Should fail without retry 2')


@tagged('-standard', 'test_retry', 'test_retry_disable')
class TestRetry2Disable(TestRetryCommon):

    def test_retry_second_class_fails(self):
        raise Exception('Should fail without retry other class')
