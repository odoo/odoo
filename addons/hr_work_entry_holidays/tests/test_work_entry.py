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
        contract = cls.env['hr.contract'].create({
            'date_start': cls.start.date() - relativedelta(days=5),
            'name': 'dodo',
            'resource_calendar_id': cls.resource_calendar_id.id,
            'wage': 1000,
            'employee_id': cls.richard_emp.id,
            'state': 'open',
            'date_generated_from': cls.end.date() + relativedelta(days=5),
        })
        cls.richard_emp.resource_calendar_id = cls.resource_calendar_id
        cls.richard_emp.contract_id = contract

    def test_validate_non_approved_leave_work_entry(self):
        work_entry1 = self.env['hr.work.entry'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'work_entry_type_id': self.work_entry_type_leave.id,
            'contract_id': self.richard_emp.contract_id.id,
            'date_start': self.start,
            'date_stop': self.end,
        })
        self.env['hr.leave'].create({
            'name': 'Doctor Appointment',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': self.start.date() - relativedelta(days=1),
            'request_date_to': self.start.date(),
        })
        self.assertFalse(work_entry1.action_validate(), "It should not validate work_entries conflicting with non approved leaves")
        self.assertEqual(work_entry1.state, 'conflict')

    def test_refuse_leave_work_entry(self):
        start = datetime(2015, 11, 1, 9, 0, 0)
        end = datetime(2015, 11, 3, 13, 0, 0)
        leave = self.env['hr.leave'].create({
            'name': 'Doctor Appointment',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': start,
            'request_date_to': start + relativedelta(days=1),
        })
        work_entry = self.env['hr.work.entry'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'contract_id': self.richard_emp.contract_id.id,
            'work_entry_type_id': self.work_entry_type.id,
            'date_start': start,
            'date_stop': end,
            'leave_id': leave.id
        })
        work_entry.action_validate()
        self.assertEqual(work_entry.state, 'conflict', "It should have an error (conflicting leave to approve")
        leave.action_refuse()
        self.assertNotEqual(work_entry.state, 'conflict', "It should not have an error")

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
        leave.action_validate()

        work_entries = self.richard_emp.contract_id.generate_work_entries(self.start.date(), self.end.date())
        work_entries.action_validate()
        leave_work_entry = work_entries.filtered(lambda we: we.work_entry_type_id in self.work_entry_type_leave)
        sum_hours = sum(leave_work_entry.mapped('duration'))

        self.assertEqual(sum_hours, 5.0, "It should equal the number of hours richard should have worked")

    def test_contract_on_another_company(self):
        """ Test that the work entry generation still work if
            the contract is not on the same company than
            the employee (Internal Use Case)
            So when generating the work entries in Belgium,
            there is an issue when accessing to the time off
            in Hong Kong.
        """
        company = self.env['res.company'].create({'name': 'Another Company'})

        employee = self.env['hr.employee'].create({
            'name': 'New Employee',
            'company_id': company.id,
        })

        self.env['hr.contract'].create({
            'name': 'Employee Contract',
            'employee_id': employee.id,
            'date_start': Date.from_string('2015-01-01'),
            'state': 'open',
            'company_id': self.env.ref('base.main_company').id,
            'wage': 4000,
        })

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Sick',
            'request_unit': 'hour',
            'leave_validation_type': 'both',
            'requires_allocation': 'no',
            'company_id': company.id,
        })
        leave1 = self.env['hr.leave'].create({
            'name': 'Sick 1 week during christmas snif',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': '2019-12-23',
            'request_date_to': '2019-12-27',
        })
        leave1.action_approve()
        leave1.action_validate()

        # The work entries generation shouldn't raise an error

        user = self.env['res.users'].create({
            'name': 'Classic User',
            'login': 'Classic User',
            'company_id': self.env.ref('base.main_company').id,
            'company_ids': self.env.ref('base.main_company').ids,
            'groups_id': [(6, 0, [self.env.ref('hr_contract.group_hr_contract_manager').id, self.env.ref('base.group_user').id])],
        })
        self.env['hr.employee'].with_user(user).generate_work_entries('2019-12-01', '2019-12-31')

    def test_work_entries_generation_if_parent_leave_zero_hours(self):
        # Test case: The employee has a parental leave at 0 hours per week
        # The employee has a leave during that period

        employee = self.env['hr.employee'].create({'name': 'My employee'})
        calendar = self.env['resource.calendar'].create({
            'name': 'Parental 0h',
            'attendance_ids': False,
        })
        employee.resource_calendar_id = calendar
        contract = self.env['hr.contract'].create({
            'date_start': self.start.date() - relativedelta(years=1),
            'name': 'Contract - Parental 0h',
            'resource_calendar_id': calendar.id,
            'wage': 1000,
            'employee_id': employee.id,
            'state': 'open',
        })

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Sick',
            'request_unit': 'hour',
            'leave_validation_type': 'both',
            'requires_allocation': 'no',
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
        with self.assertRaises(ValidationError), self.cr.savepoint():
            leave.action_approve()
            leave.action_validate()

        work_entries = contract.generate_work_entries(date(2020, 7, 1), date(2020, 9, 30))

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
        leave.action_validate()

        self.richard_emp.generate_work_entries(date_from, date_to, True)
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.richard_emp.id),
            ('date_stop', '>=', date_from),
            ('date_start', '<=', date_to),
            ('state', '!=', 'validated')])
        leave_work_entry = work_entries.filtered(lambda we: we.work_entry_type_id in self.work_entry_type_leave)
        self.assertEqual(leave_work_entry.leave_id.id, leave.id, "Leave work entry should have leave_id value")

        public_holiday_work_entry = work_entries.filtered(lambda we: we.work_entry_type_id == work_entry_type_holiday)
        self.assertEqual(len(public_holiday_work_entry.leave_id), 0, "Public holiday work entry should not have leave_id")
