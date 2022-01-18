# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import BaseCase, tagged

import logging
import os

_logger = logging.getLogger(__name__)


class TestRetryCommon(BaseCase):
    def get_tests_run_count(self):
        return int(os.environ.get('ODOO_TEST_FAILURE_RETRIES', 0)) + 1

    def update_count(self):
        self.count = getattr(self, 'count', 0) + 1


@tagged('-standard', 'test_retry', 'test_retry_success')
class TestRetry(TestRetryCommon):
    """ Check some tests behaviour when ODOO_TEST_FAILURE_RETRIES is set"""

    def test_log_levels(self):
        _logger.debug('test debug')
        _logger.info('test info')
        _logger.runbot('test 25')

    def test_retry_success(self):
        tests_run_count = self.get_tests_run_count()
        self.update_count()
        if tests_run_count != self.count:
            _logger.error('Failure')
        self.assertEqual(tests_run_count, self.count)


@tagged('-standard', 'test_retry', 'test_retry_failures')
class TestRetryFailures(TestRetryCommon):
    def test_retry_failure_assert(self):
        self.assertFalse(1 == 1)

    def test_retry_failure_log(self):
        _logger.error('Failure')


@tagged('-standard', 'test_retry', 'test_retry_success')
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
