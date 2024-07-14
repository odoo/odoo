# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import time

from freezegun import freeze_time
from logging import getLogger

from odoo.addons.appointment.tests.test_performance import AppointmentUIPerformanceCase
from odoo.addons.appointment_hr.tests.test_performance import AppointmenHrPerformanceCase
from odoo.tests import tagged
from odoo.tests.common import warmup

_logger = getLogger(__name__)


@tagged('appointment_performance', 'post_install', '-at_install')
class OnelineWAppointmentPerformance(AppointmentUIPerformanceCase, AppointmenHrPerformanceCase):

    @classmethod
    def setUpClass(cls):
        super(OnelineWAppointmentPerformance, cls).setUpClass()
        cls.test_apt_type.is_published = True
        cls.test_apt_type_resource = cls.env['appointment.type'].create({
            'appointment_tz': 'Europe/Brussels',
            'appointment_duration': 1,
            'assign_method': 'time_auto_assign',
            'category': 'recurring',
            'is_published': True,
            'max_schedule_days': 60,
            'min_cancellation_hours': 1,
            'min_schedule_hours': 1,
            'name': 'Test Appointment Type Resource',
            'schedule_based_on': 'resources',
            'slot_ids': [
                (0, 0, {'end_hour': hour + 1,
                        'start_hour': hour,
                        'weekday': weekday,
                        })
                for weekday in ['1', '2', '3', '4', '5']
                for hour in range(8, 16)
            ],
            'resource_ids': [(4, resource.id) for resource in cls.resources],
            'work_hours_activated': True,
        })

    def setUp(self):
        super().setUp()
        # Flush everything, notably tracking values, as it may impact performances
        self.flush_tracking()

    @warmup
    def test_appointment_type_page_website_whours_public(self):
        random.seed(1871)  # fix shuffle in _slots_fill_users_availability

        t0 = time.time()
        with freeze_time(self.reference_now):
            self.authenticate(None, None)
            with self.assertQueryCount(default=37):
                self._test_url_open('/appointment/%i' % self.test_apt_type.id)
        t1 = time.time()

        _logger.info('Browsed /appointment/%i, time %.3f', self.test_apt_type.id, t1 - t0)
        # Time before optimization: ~1.90 (but with boilerplate)
        # Time after optimization: ~0.50 (but with boilerplate)

    @warmup
    def test_appointment_type_page_website_whours_user(self):
        random.seed(1871)  # fix shuffle in _slots_fill_users_availability

        t0 = time.time()
        with freeze_time(self.reference_now):
            self.authenticate('staff_user_bxls', 'staff_user_bxls')
            with self.assertQueryCount(default=50):  # apt only: 42 / +1 for no-demo
                self._test_url_open('/appointment/%i' % self.test_apt_type.id)
        t1 = time.time()

        _logger.info('Browsed /appointment/%i, time %.3f', self.test_apt_type.id, t1 - t0)
        # Time before optimization: ~1.90 (but with boilerplate)
        # Time before optimization: ~0.70 (but with boilerplate)

    @warmup
    def test_appointment_type_resource_page_website_whours_public(self):
        random.seed(1871)

        t0 = time.time()
        with freeze_time(self.reference_now):
            self.authenticate(None, None)
            with self.assertQueryCount(default=36):
                self._test_url_open('/appointment/%i' % self.test_apt_type_resource.id)
        t1 = time.time()
        _logger.info('Browsed /appointment/%i, time %.3f', self.test_apt_type_resource.id, t1 - t0)

    @warmup
    def test_appointment_type_resource_page_website_whours_user(self):
        random.seed(1871)

        t0 = time.time()
        with freeze_time(self.reference_now):
            self.authenticate('staff_user_bxls', 'staff_user_bxls')
            with self.assertQueryCount(default=45):  # apt only: 36 / +1 for no-demo
                self._test_url_open('/appointment/%i' % self.test_apt_type_resource.id)
        t1 = time.time()

        _logger.info('Browsed /appointment/%i, time %.3f', self.test_apt_type_resource.id, t1 - t0)
