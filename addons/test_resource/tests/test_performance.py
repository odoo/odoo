# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time
import pytz

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.tests import TransactionCase, warmup

_logger = logging.getLogger(__name__)

class TestResourcePerformance(TransactionCase):

    @warmup
    def test_performance_attendance_intervals_batch(self):
        # Tests the performance of _attendance_intervals_batch with a batch of 100 resources
        calendar = self.env['resource.calendar'].create({
            'name': 'Calendar',
        })
        resources = self.env['resource.test'].create([
            {
                'name': 'Resource ' + str(i),
                'resource_calendar_id': calendar.id,
            }
            for i in range(100)
        ])
        with self.assertQueryCount(__system__=1):
            # Generate attendances for a whole year
            start = pytz.utc.localize(datetime.now() + relativedelta(month=1, day=1))
            stop = pytz.utc.localize(datetime.now() + relativedelta(month=12, day=31))
            start_time = time.time()
            calendar._attendance_intervals_batch(start, stop, resources=resources.resource_id)
            _logger.info('Attendance Intervals Batch (100): --- %s seconds ---', time.time() - start_time)
            # Before
            #INFO master test_performance: Attendance Intervals Batch (100): --- 2.0667169094085693 seconds ---
            #INFO master test_performance: Attendance Intervals Batch (100): --- 2.0868310928344727 seconds ---
            #INFO master test_performance: Attendance Intervals Batch (100): --- 1.9209258556365967 seconds ---
            #INFO master test_performance: Attendance Intervals Batch (100): --- 1.9474620819091797 seconds ---
            # After
            #INFO master test_performance: Attendance Intervals Batch (100): --- 0.4092371463775635 seconds ---
            #INFO master test_performance: Attendance Intervals Batch (100): --- 0.3598649501800537 seconds ---
