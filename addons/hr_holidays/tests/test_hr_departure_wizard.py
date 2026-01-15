# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, timedelta

from odoo import Command
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestHolidaysFlow(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Sky'
        })
        cls.departure_date = date.today()
        departure_reason = cls.env['hr.departure.reason'].create({'name': "Fired"})
        cls.departure_wizard = cls.env['hr.departure.wizard'].create({
            'departure_reason_id': departure_reason.id,
            'departure_date': cls.departure_date,
            'employee_ids': [Command.link(cls.employee.id)],
        })
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'time_type': 'leave',
            'requires_allocation': False,
        })

    def test_departure_without_leave_and_allocation_employee(self):
        self._check_action_departure()

    def test_departure_leave_before_departure_date(self):
        leave = self.env['hr.leave'].with_context(leave_fast_create=True).create({
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': self.departure_date + timedelta(days=-6),
            'request_date_to': self.departure_date,
        })
        leave.state = 'validate'

        self._check_action_departure()

    def test_departure_leave_after_departure_date(self):
        leave = self.env['hr.leave'].with_context(leave_fast_create=True).create({
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': self.departure_date + timedelta(days=6),
            'request_date_to': self.departure_date + timedelta(days=8),
        })
        leave.state = 'validate'

        self._check_action_departure()

    def test_departure_leave_with_departure_date(self):
        leave = self.env['hr.leave'].with_context(leave_fast_create=True).create({
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': self.departure_date + timedelta(days=-6),
            'request_date_to': self.departure_date + timedelta(days=8),
        })
        leave.state = 'validate'

        self._check_action_departure()
        message = "<p>End date has been updated because the employee will leave the company on %(departure_date)s.</p>" % {
            'departure_date': self.departure_date}
        self.assertTrue(message in leave.message_ids.mapped('body'))

        cancel_message = "<p>The time off request has been cancelled for the following reason:</p><p>The employee will leave the company on %(departure_date)s.</p>" % {
            'departure_date': self.departure_date
        }
        self.assertTrue(cancel_message in self.env['hr.leave'].search([
            ('request_date_from', '=', self.departure_date + timedelta(days=1)),
            ('request_date_to', '=', self.departure_date + timedelta(days=8)),
            ("employee_id", "=", self.employee.id)
        ]).message_ids.mapped('body'))

    def test_departure_allocation_before_departure_date(self):
        self.env['hr.leave.allocation'].create([{
            'name': 'allocation',
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 15,
            'employee_id': self.employee.id,
            'state': 'confirm',
            'date_from': self.departure_date + timedelta(days=-10),
            'date_to': self.departure_date,
        }]).action_approve()
        self._check_action_departure()

    def test_departure_allocation_after_departure_date(self):
        self.env['hr.leave.allocation'].create([{
            'name': 'allocation',
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 15,
            'employee_id': self.employee.id,
            'state': 'confirm',
            'date_from': self.departure_date + timedelta(days=1),
            'date_to': self.departure_date + timedelta(days=10),
        }]).action_approve()
        self._check_action_departure()

    def test_departure_allocation_with_departure_date(self):
        allocation = self.env['hr.leave.allocation'].create([{
            'name': 'allocation',
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 15,
            'employee_id': self.employee.id,
            'state': 'confirm',
            'date_from': self.departure_date + timedelta(days=-10),
            'date_to': self.departure_date + timedelta(days=10),
        }])
        allocation.action_approve()
        self._check_action_departure()

        allocation_msg = '<p>Validity End date has been updated because the employee will leave the company on %(departure_date)s.</p>' % {
            'departure_date': self.departure_date
        }
        self.assertTrue(allocation_msg in allocation.message_ids.mapped('body'))

    def _check_action_departure(self):
        self.departure_wizard.action_register_departure()
        self._check_employee_allocation()
        self._check_employee_leave()

    def _check_employee_leave(self):
        leaves_after_departure_date = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee.id),
            ('date_from', '>', self.departure_date),
            ('state', '!=', 'cancel')
        ])

        self.assertFalse(leaves_after_departure_date)
        leaves_before_departure_date = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee.id),
            ('date_from', '<=', self.departure_date),
        ])
        self.assertFalse(any(leave.date_to.date() > self.departure_date for leave in leaves_before_departure_date))

    def _check_employee_allocation(self):
        allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', self.employee.id),
            '|',
                ('date_from', '>', self.departure_date),
                ('date_to', '>', self.departure_date),
        ])
        self.assertFalse(allocations)
