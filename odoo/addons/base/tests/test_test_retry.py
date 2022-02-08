# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import BaseCase, tagged

import logging
import os

_logger = logging.getLogger(__name__)

@tagged('-standard', 'test_retry', 'test_retry_success')
class TestRetry(BaseCase):
    """ Check some tests behaviour when ODOO_TEST_FAILURE_RETRIES is set"""

    def test_log_levels(self):
        _logger.debug('test debug')
        _logger.info('test info')
        _logger.runbot('test 25')

    def test_retry_success(self):
        tests_run_count = int(os.environ.get('ODOO_TEST_FAILURE_RETRIES', 0)) + 1
        self.count = getattr(self, 'count', 0) + 1
        self.assertEqual(tests_run_count, self.count)

@tagged('-standard', 'test_retry', 'test_retry_failures')
class TestRetryFailures(BaseCase):
    def test_retry_failure_assert(self):
        self.assertFalse(1 == 1)

    def test_retry_failure_log(self):
        _logger.error('Failure')
