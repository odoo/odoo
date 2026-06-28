# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time
from datetime import datetime, UTC

from dateutil.relativedelta import relativedelta

from odoo.tests import tagged, TransactionCase, warmup

_logger = logging.getLogger(__name__)


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestResourcePerformance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Calendar',
        })
        cls.resources = cls.env['resource.test'].create([
            {
                'name': 'Resource ' + str(i),
                'resource_calendar_id': cls.calendar.id,
            }
            for i in range(100)
        ])

    @warmup
    def test_performance_attendance_intervals_batch(self):
        # Tests the performance of _attendance_intervals_batch with a batch of 100 resources
        with self.assertQueryCount(__system__=3):
            # Generate attendances for a whole year
            start = datetime.now(UTC) + relativedelta(month=1, day=1)
            stop = datetime.now(UTC) + relativedelta(month=12, day=31)
            start_time = time.time()
            resources_per_tz = {
                UTC: self.resources.resource_id
            }
            self.calendar._attendance_intervals_batch(start, stop, resources_per_tz=resources_per_tz)
            _logger.info('Attendance Intervals Batch (100): --- %s seconds ---', time.time() - start_time)
            # Before - 6 queries
            # INFO master test_performance: Attendance Intervals Batch (100): --- 0.022723913192749023 seconds ---
            # INFO master test_performance: Attendance Intervals Batch (100): --- 0.02302718162536621 seconds ---
            # After - 3 queries
            # INFO master test_performance: Attendance Intervals Batch (100): --- 0.01298666000366211 seconds ---
            # INFO master test_performance: Attendance Intervals Batch (100): --- 0.011599302291870117 seconds ---
