# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_homeworking.tests.common import TestHrHomeworkingCommon

from odoo.tests import tagged
from freezegun import freeze_time
from datetime import datetime

@tagged('post_install', '-at_install', "homeworking_tests")
class TestHrHomeworkingHrEmployeeLocation(TestHrHomeworkingCommon):
    @classmethod
    def setUpClass(cls):
        super(TestHrHomeworkingHrEmployeeLocation, cls).setUpClass()
        cls.HrEmployeeLocation = cls.env['hr.employee.location']

    @freeze_time('2023-05-16')
    def test_register_location_in_the_futur_with_a_previous_worklocation(self):
        with freeze_time('2023-05-01'):
            self.HrEmployeeLocation.create({
                # tuesday
                'start_date': '2023-05-02',
                'end_date_create': '2023-05-02',
                'work_location_id': self.work_office_1.id,
                'employee_id': self.employee_hruser_id,
                'weekly': True,
            })
        self.HrEmployeeLocation.create({
            # tuesday
            'start_date': '2023-05-16',
            'end_date_create': '2023-05-16',
            'work_location_id': self.work_office_1.id,
            'employee_id': self.employee_hruser_id,
            'weekly': True,
        })
        self.env['hr.employee.location'].flush_model(['weekday'])
        location_for_emp = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        self.assertEqual(len(location_for_emp.ids), 2)
        location_for_emp_weekly = location_for_emp.filtered(lambda wl: wl.weekly)
        self.assertEqual(len(location_for_emp_weekly.ids), 2)
    @freeze_time('2023-05-16')
    def test_register_location_in_the_futur(self):
        # register a location for just one day (wednesday > today)
        self.HrEmployeeLocation.create({
            # wednesday
            'start_date': '2023-05-17',
            'end_date_create': '2023-05-17',
            'work_location_id': self.work_office_1.id,
            'employee_id': self.employee_emp_id,
        })
        self.env['hr.employee.location'].flush_model(['weekday'])
        location_for_emp = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_emp_id),
        ])
        self.assertEqual(len(location_for_emp.ids), 1)

        # register a location for just two das (thursday, friday > today)
        self.HrEmployeeLocation.create({
            # thursday
            'start_date': '2023-05-18',
            # friday
            'end_date_create': '2023-05-19',
            'work_location_id': self.work_office_2.id,
            'employee_id': self.employee_emp_id,
        })
        self.env['hr.employee.location'].flush_model(['weekday'])
        location_for_emp = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_emp_id),
        ])
        self.assertEqual(len(location_for_emp.ids), 3)

        # register a location for every saturday (saturday > today)
        self.HrEmployeeLocation.create({
            # saturday
            'start_date': '2023-05-20',
            'end_date_create': '2023-05-20',
            'work_location_id': self.work_office_1.id,
            'employee_id': self.employee_emp_id,
            'weekly': True,
        })
        self.env['hr.employee.location'].flush_model(['weekday'])
        location_for_emp = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_emp_id),
        ])
        self.assertEqual(len(location_for_emp.ids), 4)
        self.assertFalse(self.employee_emp.monday_location_id)
        self.assertFalse(self.employee_emp.tuesday_location_id)
        self.assertFalse(self.employee_emp.wednesday_location_id)
        self.assertFalse(self.employee_emp.thursday_location_id)
        self.assertFalse(self.employee_emp.friday_location_id)
        self.assertEqual(self.employee_emp.saturday_location_id, self.work_office_1)
        self.assertFalse(self.employee_hruser.sunday_location_id)

    @freeze_time('2023-05-05')
    def test_register_location_for_today(self):
        # register a location for just one day (friday == today)
        record_N_weekly_one_day = self.HrEmployeeLocation.create({
            # friday
            'start_date': '2023-05-05',
            'end_date_create': '2023-05-05',
            'work_location_id': self.work_office_1.id,
            'employee_id': self.employee_hruser_id,
        })
        self.env['hr.employee.location'].flush_model(['weekday'])
        self.assertFalse(self.employee_hruser.monday_location_id)
        self.assertFalse(self.employee_hruser.tuesday_location_id)
        self.assertFalse(self.employee_hruser.wednesday_location_id)
        self.assertFalse(self.employee_hruser.thursday_location_id)
        self.assertFalse(self.employee_hruser.friday_location_id)
        self.assertFalse(self.employee_hruser.saturday_location_id)
        self.assertFalse(self.employee_hruser.sunday_location_id)
        self.assertFalse(record_N_weekly_one_day.weekday)
        self.assertFalse(record_N_weekly_one_day.weekly)

        # register a location for 3 days (friday == today)
        self.HrEmployeeLocation.create({
            # friday
            'start_date': '2023-05-05',
            # sunday
            'end_date_create': '2023-05-07',
            'work_location_id': self.work_office_2.id,
            'employee_id': self.employee_hruser_id,
        })
        self.env['hr.employee.location'].flush_model(['weekday'])
        location_for_emp_hruser = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        friday_location = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
            ("start_date", "=", datetime(2023, 5, 5)),
        ]).work_location_id
        self.assertEqual(friday_location, self.work_office_2)
        self.assertEqual(len(location_for_emp_hruser.ids), 3)

        # register a location for every friday (friday == today)
        self.HrEmployeeLocation.create({
            # friday
            'start_date': '2023-05-05',
            'end_date_create': '2023-05-05',
            'employee_id': self.employee_hruser_id,
            'work_location_id': self.work_home.id,
            'weekly': True
        })
        self.env['hr.employee.location'].flush_model(['weekday'])
        self.assertFalse(self.employee_hruser.monday_location_id)
        self.assertFalse(self.employee_hruser.tuesday_location_id)
        self.assertFalse(self.employee_hruser.wednesday_location_id)
        self.assertFalse(self.employee_hruser.thursday_location_id)
        self.assertEqual(self.employee_hruser.friday_location_id, self.work_home)
        self.assertFalse(self.employee_hruser.saturday_location_id)
        self.assertFalse(self.employee_hruser.sunday_location_id)
        location_for_emp_hruser = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        friday_locations = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
            ("start_date", "=", datetime(2023, 5, 5)),
        ])
        # the exceptional worlocation is replaced by the default worklocation
        self.assertEqual(len(location_for_emp_hruser.ids), 3)
        self.assertEqual(len(friday_locations.ids), 1)

        # register a location for every wednesday, thursday and friday (the start of wednesday and thursday are in the past)
        # expected behavior:
        # 3 weekly record (for wednesday, thurday, friday)
        # 4 exceptionnal record (wednesday and thursday before today) + (saturday and sunday)
        self.HrEmployeeLocation.create({
            # wednesday
            'start_date': '2023-05-03',
            # friday
            'end_date_create': '2023-05-05',
            'employee_id': self.employee_hruser_id,
            'work_location_id': self.work_office_1.id,
            'weekly': True
        })
        self.env['hr.employee.location'].flush_model(['weekday'])
        self.assertFalse(self.employee_hruser.monday_location_id)
        self.assertFalse(self.employee_hruser.tuesday_location_id)
        self.assertEqual(self.employee_hruser.wednesday_location_id, self.work_office_1)
        self.assertEqual(self.employee_hruser.thursday_location_id, self.work_office_1)
        self.assertEqual(self.employee_hruser.friday_location_id, self.work_office_1)
        self.assertFalse(self.employee_hruser.saturday_location_id)
        self.assertFalse(self.employee_hruser.sunday_location_id)
        location_for_emp_hruser = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        location_exceptional = location_for_emp_hruser.filtered(lambda wl: not wl.weekly)
        self.assertEqual(len(location_for_emp_hruser.ids), 7)
        self.assertEqual(len(location_exceptional), 4)
