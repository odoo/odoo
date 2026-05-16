# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from freezegun import freeze_time
from dateutil.relativedelta import relativedelta

from odoo.tests import Form, tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('post_install', '-at_install', 'accruals')
class TestAccrualAllocationsAttendance(TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super(TestAccrualAllocationsAttendance, cls).setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'time_type': 'leave',
            'requires_allocation': True,
            'allocation_validation_type': 'hr',
        })

    def test_frequency_hourly_attendance(self):
        with freeze_time("2017-12-05"):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'is_based_on_worked_time': True,
                'can_be_carryover': True,
                'level_ids': [(0, 0, {
                    'milestone_date': 'after',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'day',
                    'frequency': 'worked_hours',
                    'cap_accrued_time': True,
                    'maximum_leave': 10000,
                    'action_with_unused_accruals': 'all',
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_approve()
            self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')
            allocation._update_accrual()
            tomorrow = datetime.date.today() + relativedelta(days=2)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet. The accrual starts tomorrow.')

            self.env['hr.attendance'].create({
                'employee_id': self.employee_emp.id,
                'check_in': datetime.datetime(2017, 12, 6, 8, 0, 0),
                'check_out': datetime.datetime(2017, 12, 6, 13, 22, 0),
            })

            with freeze_time(tomorrow):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=1)
                self.assertAlmostEqual(allocation.number_of_days, 4.37, places=2)
                self.assertEqual(allocation.nextcall, nextcall, 'The next call date of the cron should be in 2 days.')
                allocation._update_accrual()
                self.assertAlmostEqual(allocation.number_of_days, 4.37, places=2)

    def test_accrual_allocation_based_on_attendance(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].create({
            'name': 'Accrual Plan For Test',
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'end',
            'can_be_carryover': True,
            'carryover_date': 'year_start',
            'level_ids': [(0, 0, {
                'milestone_date': 'after',
                'start_count': 1,
                'added_value': 1,
                'added_value_type': 'hour',
                'frequency': 'worked_hours',
                'cap_accrued_time': True,
                'maximum_leave': 100,
                'action_with_unused_accruals': 'all',
            })],
        })
        self.env['hr.attendance'].create({
                'employee_id': self.employee_emp.id,
                'check_in': datetime.datetime(2024, 4, 1, 8, 0, 0),
                'check_out': datetime.datetime(2024, 4, 1, 17, 0, 0),
            })
        with Form(self.env['hr.leave.allocation'].with_user(self.user_hrmanager)) as allocation_form:
            allocation_form.allocation_type = 'accrual'
            allocation_form.employee_id = self.employee_emp
            allocation_form.accrual_plan_id = accrual_plan
            allocation_form.holiday_status_id = self.leave_type
            allocation_form.date_from = datetime.date(2024, 3, 20)
            allocation_form.name = 'Accrual allocation for employee'
            self.assertEqual(allocation_form.number_of_hours_display, 8.0)
            allocation_form.date_from = datetime.date(2024, 3, 25)
            allocation_form.name = 'Accrual allocation for employee'
            self.assertEqual(allocation_form.number_of_hours_display, 8.0)

    def test_accrual_allocation_with_overlapping_attendance(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].create({
            'name': 'Accrual Plan For Test',
            'is_based_on_worked_time': True,
            'accrued_gain_time': 'end',
            'carryover_date': 'year_start',
            'level_ids': [(0, 0, {
                'start_count': 0,
                'added_value': 1,
                'added_value_type': 'hour',
                'cap_accrued_time': True,
                'maximum_leave': 100,
                'frequency': 'worked_hours'
            })],
        })
        with freeze_time("2024-4-1"):
            allocation = self.env['hr.leave.allocation'].create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_approve()

        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime.datetime(2024, 4, 1, 22, 0, 0),
            'check_out': datetime.datetime(2024, 4, 2, 7, 0, 0),
        })

        with freeze_time(datetime.datetime(2024, 4, 2, 20, 0, 0)):
            # Only counts the part of the attendance on the 01/04/2024: 2 hours
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 0.25)  # 2 / 8 = 0.25

        with freeze_time(datetime.datetime(2024, 4, 3, 20, 0, 0)):
            # Counts the whole attendance: 9 hours
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 1.125)  # 9 / 8 = 1.125

    def test_accrual_allocation_with_overlapping_attendance_timezone(self):
        self.employee_emp.tz = 'Asia/Tokyo'
        self.employee_emp.resource_calendar_id.tz = 'Asia/Tokyo'
        accrual_plan = self.env['hr.leave.accrual.plan'].create({
            'name': 'Accrual Plan For Test',
            'is_based_on_worked_time': True,
            'accrued_gain_time': 'end',
            'carryover_date': 'year_start',
            'level_ids': [(0, 0, {
                'start_count': 0,
                'added_value': 1,
                'added_value_type': 'hour',
                'cap_accrued_time': True,
                'maximum_leave': 100,
                'frequency': 'worked_hours'
            })],
        })
        with freeze_time("2024-4-1"):
            allocation = self.env['hr.leave.allocation'].create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_approve()

        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime.datetime(2024, 4, 1, 22, 0, 0),  # In Tokyo: 2024/04/02, 7h
            'check_out': datetime.datetime(2024, 4, 2, 7, 0, 0),  # In Tokyo: 2024/04/02, 16h
        })

        with freeze_time(datetime.datetime(2024, 4, 2, 20, 0, 0)):
            # Only counts the part of the attendance on the 01/04/2024 UTC: 2 hours
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 0.25)  # 2 / 8 = 0.25

        with freeze_time(datetime.datetime(2024, 4, 3, 20, 0, 0)):
            # Counts the whole attendance: 9 hours - 1h of lunchtime = 8h
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 1.0)  # 8 / 8 = 1.0
