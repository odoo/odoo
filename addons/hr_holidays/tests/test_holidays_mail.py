# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.tools import mute_logger

from .common import TestHrHolidaysCommon
from odoo.tests import tagged

from odoo.addons.mail.tests.common import MailCase, MailCommon, freeze_all_time


class TestHolidaysMail(TestHrHolidaysCommon, MailCase):
    """Test that mails are correctly sent when a timeoff is taken"""

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_email_sent_when_approved(self):
        """ Testing leave request flow: limited type of leave request """
        with freeze_time('2022-01-15'):
            self.admin_employee.tz = "Europe/Brussels"

            work_entry_type_paid_time_off = self.env['hr.work.entry.type'].create({
                'name': 'Paid Time Off',
                'code': 'Paid Time Off',
                'requires_allocation': True,
                'employee_requests': False,
                'allocation_validation_type': 'hr',
                'leave_validation_type': 'both',
                'request_unit': 'day',
                'unit_of_measure': 'day',
            })

            self.env['hr.leave.allocation'].create([
                {
                    'name': 'Paid Time off for David',
                    'work_entry_type_id': work_entry_type_paid_time_off.id,
                    'number_of_days': 20,
                    'employee_id': self.employee_emp_id,
                    'state': 'confirm',
                    'date_from': time.strftime('%Y-%m-01'),
                }
            ]).action_approve()

            self.env['hr.leave.allocation'].create([
                {
                    'name': 'Paid Time off for Mitchell',
                    'work_entry_type_id': work_entry_type_paid_time_off.id,
                    'number_of_days': 20,
                    'employee_id': self.admin_employee.id,
                    'state': 'confirm',
                    'date_from': time.strftime('%Y-%m-01'),
                },
            ]).action_approve()

            leave_vals = {
                'name': 'Sick Time Off',
                'work_entry_type_id': work_entry_type_paid_time_off.id,
                'request_date_from': date.today() + relativedelta(day=2),
                'request_date_to': date.today() + relativedelta(day=3),
                'employee_id': self.admin_employee.id,
            }
            leave = self.env['hr.leave'].create(leave_vals)
            leave.action_approve()
            with self.mock_mail_gateway():
                leave.action_approve()
                admin_emails = self._new_mails.filtered(lambda x: x.partner_ids.employee_ids.id == self.admin_employee.id)
                self.assertEqual(len(admin_emails), 1, "Mitchell Admin should receive an email")
                self.assertTrue("has been accepted" in admin_emails.preview)


class TestMissedMessagesMail(MailCommon):
    def test_notify_missed_messages_presence(self):
        """Test that a partner is considered active if their main user is on leave,
        and that they are considered inactive when not on leave, based on the presence status."""
        with freeze_all_time("2026-03-13 18:00:00"):
            self.env["mail.presence"].sudo().create({
                "user_id": self.user_employee.id,
                "last_poll": fields.Datetime.now() - timedelta(days=4),
                "status": "offline",
            })
            work_entry_type = self.env['hr.work.entry.type'].create({
                'requires_allocation': False,
                'name': 'Legal Leaves',
                'code': 'Legal Leaves',
                'count_as': 'absence',
                'request_unit': 'day',
                'unit_of_measure': 'day',
            })
            employee = self.env["hr.employee"].create({
                "user_id": self.user_employee.id,
            })
            leave = self.env["hr.leave"].with_context(leave_skip_state_check=True).create({
                "request_date_from": fields.Date.today(),
                "request_date_to": fields.Date.today(),
                "employee_id": employee.id,
                "state": "validate",
                "work_entry_type_id": work_entry_type.id,
            })
            self.assertNotIn(
                self.user_employee.partner_id.id,
                [p["id"] for p in self.env["res.partner"]._get_inactive_partners_data()],
                "The employee partner should be considered active due to leave",
            )
            leave.unlink()
            self.assertIn(
                self.user_employee.partner_id.id,
                [p["id"] for p in self.env["res.partner"]._get_inactive_partners_data()],
                "The employee partner should be considered inactive when not on leave",
            )
