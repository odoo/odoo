# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import BaseCase, TransactionCase, tagged, BaseCase
from odoo.tests.suite import _logger as test_logger

import logging
import inspect

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

    def is_soft_fail(self):
        for frame in inspect.stack():
            if frame.function == 'run':
                result = frame.frame.f_locals.get('result')
                if result and hasattr(result, '_soft_fail') and result._soft_fail:
                    return True
        return False


@tagged('test_retry', 'test_retry_success')
class TestRetry(TestRetryCommon):
    """ Check some tests behaviour when ODOO_TEST_FAILURE_RETRIES is set"""

    def test_log_levels(self):
        _logger.debug('test debug')
        _logger.info('test info')

    def test_retry_success(self):
        if self.is_soft_fail():
            _logger.error('Failure')


@tagged('test_retry', 'test_retry_success')
class TestRetryTraceback(TestRetryCommon):
    """ Check some tests behaviour when ODOO_TEST_FAILURE_RETRIES is set"""

    def test_retry_traceback_success(self):
        if self.is_soft_fail():
            _logger.error('Traceback (most recent call last):\n')


@tagged('test_retry', 'test_retry_success')
class TestRetryTracebackArg(TestRetryCommon):
    def test_retry_traceback_args_success(self):
        if self.is_soft_fail():
            _logger.error('%s', 'Traceback (most recent call last):\n')


@tagged('-standard', 'test_retry', 'test_retry_failures')
class TestRetryFailures(TestRetryCommon):
    def test_retry_failure_assert(self):
        self.assertFalse(1 == 1)

    def test_retry_failure_log(self):
        _logger.error('Failure')


@tagged('test_retry', 'test_retry_success')
class TestRetryRollbackedCursor(TestRetryCommon, TransactionCase):
    def test_broken_cursor(self):
        if self.is_soft_fail():
            self.env.cr.rollback()


@tagged('test_retry', 'test_retry_success')
class TestRetryCommitedCursor(TestRetryCommon, TransactionCase):
    def test_broken_cursor(self):
        if self.is_soft_fail():
            self.env.cr.commit()


@tagged('test_retry', 'test_retry_success')
class TestRetryRollbackedCursorError(TestRetryCommon, TransactionCase):
    def test_broken_cursor(self):
        if self.is_soft_fail():
            self.env.cr.rollback()
            raise Exception('a')


@tagged('test_retry', 'test_retry_success')
class TestRetryCommitedCursorError(TestRetryCommon, TransactionCase):
    def test_broken_cursor(self):
        if self.is_soft_fail():
            self.env.cr.commit()
            raise Exception('a')


@tagged('test_retry', 'test_retry_success')
class TestRetrySubtest(TestRetryCommon):

    def test_retry_subtest_success_one(self):
        is_soft_fail = self.is_soft_fail()
        for i in range(3):
            if i == 1:
                with self.subTest():
                    if is_soft_fail:
                        _logger.error('Failure')


@tagged('test_retry', 'test_retry_success')
class TestRetrySubtestAll(TestRetryCommon):
    def test_retry_subtest_success_all(self):
        is_soft_fail = self.is_soft_fail()
        for _ in range(3):
            with self.subTest():
                if is_soft_fail:
                    _logger.error('Failure')


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
        if self.is_soft_fail():
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
