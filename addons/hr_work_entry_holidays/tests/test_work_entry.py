# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import pytz

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged
from odoo.fields import Date
from odoo.addons.hr_work_entry_holidays.tests.common import TestWorkEntryHolidaysBase


@tagged('work_entry')
class TestWorkeEntryHolidaysWorkEntry(TestWorkEntryHolidaysBase):
    @classmethod
    def setUpClass(cls):
        super(TestWorkeEntryHolidaysWorkEntry, cls).setUpClass()
        cls.tz = pytz.timezone(cls.richard_emp.tz)
        cls.start = datetime(2015, 11, 1, 1, 0, 0)
        cls.end = datetime(2015, 11, 30, 23, 59, 59)
        cls.resource_calendar_id = cls.env['resource.calendar'].create({'name': 'Zboub'})
        cls.richard_emp.create_version({
            'date_version': cls.start.date() - relativedelta(days=5),
            'contract_date_start': cls.start.date() - relativedelta(days=5),
            'contract_date_end': Date.to_date('2017-12-31'),
            'name': 'dodo',
            'resource_calendar_id': cls.resource_calendar_id.id,
            'wage': 1000,
            'date_generated_from': cls.end.date() + relativedelta(days=5),
        })

    def test_time_week_leave_work_entry(self):
        # /!\ this is a week day => it exists an calendar attendance at this time
        leave = self.env['hr.leave'].create({
            'name': '1leave',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2015, 11, 2),
            'request_date_to': date(2015, 11, 2),
            'request_unit_hours': True,
            'request_hour_from': 11,
            'request_hour_to': 17,
        })
        leave.action_approve()

        work_entries = self.richard_emp.generate_work_entries(self.start.date(), self.end.date())
        work_entries.action_validate()
        leave_work_entry = work_entries.filtered(lambda we: we.work_entry_type_id in self.work_entry_type_leave)
        sum_hours = sum(leave_work_entry.mapped('duration'))

        self.assertEqual(sum_hours, 5.0, "It should equal the number of hours richard should have worked")

    def test_work_entries_generation_if_parent_leave_zero_hours(self):
        # Test case: The employee has a parental leave at 0 hours per week
        # The employee has a leave during that period

        calendar = self.env['resource.calendar'].create({
            'name': 'Parental 0h',
            'attendance_ids': False,
        })
        employee = self.env['hr.employee'].create({
            'name': 'My employee',
            'contract_date_start': self.start.date() - relativedelta(years=1),
            'contract_date_end': False,
            'resource_calendar_id': calendar.id,
            'wage': 1000,
        })

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Sick',
            'request_unit': 'hour',
            'leave_validation_type': 'both',
            'requires_allocation': False,
        })

        leave = self.env['hr.leave'].create({
            'name': "Sick 1 that doesn't make sense, but it's the prod so YOLO",
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': date(2020, 9, 4),
            'request_date_to': date(2020, 9, 4),
        })

        # TODO I don't know what this test is supposed to test, but I feel that
        # in any case it should raise a Validation Error, as it's trying to
        # validate a leave in a period the employee is not supposed to work.
        with self.assertRaises(ValidationError):
            leave.action_approve()

        work_entries = employee.version_id.generate_work_entries(date(2020, 7, 1), date(2020, 9, 30))

        self.assertEqual(len(work_entries), 0)

    def test_work_entries_leave_if_leave_conflict_with_public_holiday(self):
        date_from = datetime(2023, 2, 1, 0, 0, 0)
        date_to = datetime(2023, 2, 28, 23, 59, 59)
        work_entry_type_holiday = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday',
            'is_leave': True,
            'code': 'LEAVETEST500'
        })
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2023, 2, 6, 0, 0, 0),
            'date_to': datetime(2023, 2, 7, 23, 59, 59),
            'calendar_id': self.richard_emp.resource_calendar_id.id,
            'work_entry_type_id': work_entry_type_holiday.id,
        })
        leave = self.env['hr.leave'].create({
            'name': 'AL',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2023, 2, 3),
            'request_date_to': date(2023, 2, 9),
        })
        leave.action_approve()

        self.richard_emp.generate_work_entries(date_from, date_to, True)
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.richard_emp.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '!=', 'validated')])
        leave_work_entry = work_entries.filtered(lambda we: we.work_entry_type_id in self.work_entry_type_leave)
        self.assertEqual(leave_work_entry.leave_id.id, leave.id, "Leave work entry should have leave_id value")

        public_holiday_work_entry = work_entries.filtered(lambda we: we.work_entry_type_id == work_entry_type_holiday)
        self.assertEqual(len(public_holiday_work_entry.leave_id), 0, "Public holiday work entry should not have leave_id")
