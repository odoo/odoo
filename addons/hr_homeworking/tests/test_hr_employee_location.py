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
    def test_register_removed_worklocation(self):
        record_to_removed_one_date = self.HrEmployeeLocation.create({
            # tuesday
            'start_date': '2023-05-16',
            'end_date_create': '2023-05-16',
            'work_location_id': self.work_office_2.id,
            'employee_id': self.employee_hruser_id,
            'weekly': True,
        })
        record_to_removed_one_date.add_removed_work_location(datetime(2023, 5, 30))
        location_for_hruser = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        self.assertEqual(self.employee_hruser.tuesday_location_id.id, self.work_office_2.id)
        self.assertEqual(len(location_for_hruser.ids), 2)
        location_weekly = location_for_hruser.filtered(lambda wl: wl.weekly)
        location_removed = location_for_hruser - location_weekly
        self.assertEqual(len(location_weekly), 1)
        self.assertEqual(record_to_removed_one_date.child_removed_ids, location_removed)
        record_to_removed_one_date.delete_default_worklocation()
        no_location = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        self.assertEqual(len(no_location.ids), 0)
        self.assertFalse(self.employee_hruser.tuesday_location_id)

    @freeze_time('2023-05-16')
    def test_register_exception_after_removed_worklocation(self):
        record_to_removed_one_date = self.HrEmployeeLocation.create({
            # tuesday
            'start_date': '2023-05-16',
            'end_date_create': '2023-05-16',
            'work_location_id': self.work_office_2.id,
            'employee_id': self.employee_hruser_id,
            'weekly': True,
        })
        record_to_removed_one_date.add_removed_work_location(datetime(2023, 5, 30))
        self.HrEmployeeLocation.create({
            # tuesday
            'start_date': '2023-05-30',
            'end_date_create': '2023-05-30',
            'work_location_id': self.work_office_1.id,
            'employee_id': self.employee_hruser_id,
        })
        location_for_hruser = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        self.assertEqual(len(location_for_hruser.ids), 2)

    @freeze_time('2023-05-16')
    def test_register_location_in_the_past_with_a_previous_worklocation_on_today(self):
        self.HrEmployeeLocation.create({
            # tuesday
            'start_date': '2023-05-16',
            'end_date_create': '2023-05-16',
            'work_location_id': self.work_office_2.id,
            'employee_id': self.employee_hruser_id,
            'weekly': True,
        })
        self.HrEmployeeLocation.create({
            # tuesday
            'start_date': '2023-05-02',
            'end_date_create': '2023-05-02',
            'work_location_id': self.work_home.id,
            'employee_id': self.employee_hruser_id,
            'weekly': True,
        })
        location_for_hruser = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        self.assertEqual(len(location_for_hruser.ids), 2)
        self.assertEqual(len(location_for_hruser.filtered(lambda wl: wl.weekly).ids), 1)
        self.assertEqual(self.employee_hruser.tuesday_location_id.id, self.work_home.id)

    @freeze_time('2023-05-16')
    def test_register_location_in_the_past_with_a_previous_worklocation_in_the_futur(self):
        self.HrEmployeeLocation.create({
            # wednesday
            'start_date': '2023-05-17',
            'end_date_create': '2023-05-17',
            'work_location_id': self.work_office_2.id,
            'employee_id': self.employee_emp_id,
            'weekly': True,
        })
        self.HrEmployeeLocation.create({
            # wednesday
            'start_date': '2023-05-03',
            'end_date_create': '2023-05-03',
            'work_location_id': self.work_home.id,
            'employee_id': self.employee_emp_id,
            'weekly': True,
        })
        location_for_emp = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_emp_id),
        ])
        self.assertEqual(len(location_for_emp.ids), 2)
        self.assertEqual(len(location_for_emp.filtered(lambda wl: wl.weekly).ids), 1)
        self.assertEqual(self.employee_emp.wednesday_location_id.id, self.work_home.id)

    @freeze_time('2023-05-30')
    def test_register_location_in_the_past_with_a_previous_worklocation_in_the_past(self):
        with freeze_time('2023-05-03'):
            self.HrEmployeeLocation.create({
                # friday
                'start_date': '2023-05-05',
                'end_date_create': '2023-05-05',
                'work_location_id': self.work_office_2.id,
                'employee_id': self.employee_emp_id,
                'weekly': True,
            })
        self.HrEmployeeLocation.create({
            # friday
            'start_date': '2023-05-19',
            'end_date_create': '2023-05-19',
            'work_location_id': self.work_home.id,
            'employee_id': self.employee_emp_id,
            'weekly': True,
        })
        location_for_emp = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_emp_id),
        ])
        self.assertEqual(len(location_for_emp.ids), 3)
        self.assertEqual(len(location_for_emp.filtered(lambda wl: wl.weekly).ids), 2)
        save_location = location_for_emp.filtered(lambda wl: not wl.current_location)
        self.assertEqual(len(save_location.ids), 1)
        self.assertEqual(save_location.start_date, datetime(2023, 5, 5).date())
        self.assertEqual(save_location.end_date, datetime(2023, 5, 29).date())
        self.assertEqual(self.employee_emp.friday_location_id.id, self.work_home.id)

    @freeze_time('2023-05-16')
    def test_register_location_on_today_with_a_previous_worklocation_on_today(self):
        with freeze_time('2023-05-03'):
            self.HrEmployeeLocation.create({
                # tuesday
                'start_date': '2023-05-16',
                'end_date_create': '2023-05-16',
                'work_location_id': self.work_office_2.id,
                'employee_id': self.employee_hruser_id,
                'weekly': True,
            })
        self.HrEmployeeLocation.create({
            # tuesday
            'start_date': '2023-05-16',
            'end_date_create': '2023-05-16',
            'work_location_id': self.work_home.id,
            'employee_id': self.employee_hruser_id,
            'weekly': True,
        })
        location_for_hr_user = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        self.assertEqual(len(location_for_hr_user.ids), 1)
        self.assertEqual(location_for_hr_user.start_date, datetime(2023, 5, 16).date())
        self.assertEqual(self.employee_hruser.tuesday_location_id.id, self.work_home.id)

    @freeze_time('2023-05-16')
    def test_register_location_in_the_futur_with_a_previous_worklocation_in_the_futur(self):
        self.HrEmployeeLocation.create({
            # tuesday
            'start_date': '2023-05-16',
            'end_date_create': '2023-05-16',
            'work_location_id': self.work_office_2.id,
            'employee_id': self.employee_hruser_id,
            'weekly': True,
        })
        self.HrEmployeeLocation.create({
            # tuesday
            'start_date': '2023-05-30',
            'end_date_create': '2023-05-30',
            'work_location_id': self.work_office_1.id,
            'employee_id': self.employee_hruser_id,
            'weekly': True,
        })
        location_for_hruser = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        self.assertEqual(len(location_for_hruser.ids), 1)
        self.assertEqual(location_for_hruser.start_date, datetime(2023, 5, 30).date())
        self.assertEqual(self.employee_hruser.tuesday_location_id.id, self.work_office_1.id)

        self.HrEmployeeLocation.create({
            # wednesday
            'start_date': '2023-05-17',
            'end_date_create': '2023-05-17',
            'work_location_id': self.work_office_2.id,
            'employee_id': self.employee_emp_id,
            'weekly': True,
        })
        self.HrEmployeeLocation.create({
            # wednesday
            'start_date': '2023-05-24',
            'end_date_create': '2023-05-24',
            'work_location_id': self.work_office_1.id,
            'employee_id': self.employee_emp_id,
            'weekly': True,
        })
        location_for_emp = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_emp_id),
        ])
        self.assertEqual(len(location_for_emp.ids), 1)
        self.assertEqual(location_for_emp.start_date, datetime(2023, 5, 24).date())
        self.assertEqual(self.employee_emp.wednesday_location_id.id, self.work_office_1.id)

        self.HrEmployeeLocation.create({
            # thursday
            'start_date': '2023-05-25',
            'end_date_create': '2023-05-25',
            'work_location_id': self.work_office_1.id,
            'employee_id': self.employee_hrmanager_id,
            'weekly': True,
        })
        self.HrEmployeeLocation.create({
            # thursday
            'start_date': '2023-05-18',
            'end_date_create': '2023-05-18',
            'work_location_id': self.work_office_2.id,
            'employee_id': self.employee_hrmanager_id,
            'weekly': True,
        })
        location_for_hr_manager = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hrmanager_id),
        ])
        self.assertEqual(len(location_for_hr_manager.ids), 1)
        self.assertEqual(location_for_hr_manager.start_date, datetime(2023, 5, 18).date())
        self.assertEqual(self.employee_hrmanager.thursday_location_id.id, self.work_office_2.id)

    @freeze_time('2023-05-16')
    def test_register_location_in_the_futur_with_a_previous_worklocation_in_past(self):
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
            'work_location_id': self.work_office_2.id,
            'employee_id': self.employee_hruser_id,
            'weekly': True,
        })
        location_for_hruser = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        self.assertEqual(len(location_for_hruser.ids), 2)
        location_for_hruser_weekly = location_for_hruser.filtered(lambda wl: wl.weekly)
        self.assertEqual(len(location_for_hruser_weekly.ids), 2)
        location_for_hruser_current = location_for_hruser.filtered(lambda wl: wl.current_location)
        self.assertEqual(len(location_for_hruser_current.ids), 1)
        location_save_old_location = location_for_hruser - location_for_hruser_current
        self.assertEqual(location_save_old_location.start_date, datetime(2023, 5, 2).date())
        self.assertEqual(location_save_old_location.end_date, datetime(2023, 5, 15).date())
        self.assertEqual(location_save_old_location.work_location_id.id, self.work_office_1.id)

        with freeze_time('2023-05-03'):
            self.HrEmployeeLocation.create({
                # friday
                'start_date': '2023-05-05',
                'end_date_create': '2023-05-05',
                'work_location_id': self.work_home.id,
                'employee_id': self.employee_emp_id,
                'weekly': True,
            })
        self.HrEmployeeLocation.create({
            # wednesday-friday
            'start_date': '2023-05-17',
            'end_date_create': '2023-05-19',
            'work_location_id': self.work_office_2.id,
            'employee_id': self.employee_emp_id,
            'weekly': True,
        })
        location_for_emp = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_emp_id),
        ])
        self.assertEqual(len(location_for_emp.ids), 4)
        location_for_emp_weekly = location_for_emp.filtered(lambda wl: wl.weekly)
        self.assertEqual(len(location_for_emp_weekly.ids), 4)
        location_for_emp_current = location_for_emp.filtered(lambda wl: wl.current_location)
        self.assertEqual(len(location_for_emp_current.ids), 3)
        location_save_old_location = location_for_emp - location_for_emp_current
        self.assertEqual(location_save_old_location.start_date, datetime(2023, 5, 5).date())
        self.assertEqual(location_save_old_location.end_date, datetime(2023, 5, 15).date())
        self.assertEqual(location_save_old_location.work_location_id.id, self.work_home.id)

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
