# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import date
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command
from odoo.tools import mute_logger

from .common import TestHrHolidaysCommon
from odoo.tests import tagged

from odoo.addons.mail.tests.common import MailCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestHolidaysMail(TestHrHolidaysCommon, MailCase):
    """Test that mails are correctly sent when a timeoff is taken"""

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_email_sent_when_approved(self):
        """ Testing leave request flow: limited type of leave request """
        with freeze_time('2022-01-15'):
            self.admin_employee.tz = "Europe/Brussels"

            holiday_status_paid_time_off = self.env['hr.leave.type'].create({
                'name': 'Paid Time Off',
                'requires_allocation': True,
                'employee_requests': False,
                'allocation_validation_type': 'hr',
                'leave_validation_type': 'both',
                'responsible_ids': [Command.link(self.env.ref('base.user_admin').id)],
            })

            self.env['hr.leave.allocation'].create([
                {
                    'name': 'Paid Time off for David',
                    'holiday_status_id': holiday_status_paid_time_off.id,
                    'number_of_days': 20,
                    'employee_id': self.employee_emp_id,
                    'state': 'confirm',
                    'date_from': time.strftime('%Y-%m-01'),
                }
            ]).action_approve()

            self.env['hr.leave.allocation'].create([
                {
                    'name': 'Paid Time off for Mitchell',
                    'holiday_status_id': holiday_status_paid_time_off.id,
                    'number_of_days': 20,
                    'employee_id': self.admin_employee.id,
                    'state': 'confirm',
                    'date_from': time.strftime('%Y-%m-01'),
                },
            ]).action_approve()

            leave_vals = {
                'name': 'Sick Time Off',
                'holiday_status_id': holiday_status_paid_time_off.id,
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

    def test_notify_time_off_officers_on_creation_enabled(self):
        """When notify_time_off_officers is enabled on the type, time off officers in the same company get notified on creation."""
        with freeze_time('2022-06-10'):
            leave_type = self.env['hr.leave.type'].create({
                'name': 'Paid Time Off',
                'notify_time_off_officers': True,
                'requires_allocation': False,
            })

            with self.mock_mail_gateway():
                self.env['hr.leave'].create({
                    'name': 'Paid Time Off Request',
                    'holiday_status_id': leave_type.id,
                    'request_date_from': date.today() + relativedelta(days=1),
                    'request_date_to': date.today() + relativedelta(days=2),
                    'employee_id': self.employee_emp_id,
                })
                self.assertTrue(
                    any('New Time Off Request' in m.subject for m in self._new_mails),
                        "Expected officer notification was not sent"
                    )
                officer_partner_ids = (self.user_hruser.partner_id | self.user_hrmanager.partner_id).ids
                recipient_partner_ids = self._new_mails.recipient_ids.ids
                self.assertEqual(
                    recipient_partner_ids,
                    officer_partner_ids,
                    "Recipients should match time-off officers",
                )

    def test_notify_time_off_officers_on_creation_disabled(self):
        """When notify_time_off_officers is disabled, no officer notification is sent on creation."""
        with freeze_time('2022-06-10'):
            leave_type = self.env['hr.leave.type'].create({
                'name': 'Paid Time Off',
                'notify_time_off_officers': False,
                'requires_allocation': False,
            })

            with self.mock_mail_gateway():
                self.env['hr.leave'].create({
                    'name': 'Paid Time Off Request',
                    'holiday_status_id': leave_type.id,
                    'request_date_from': date.today() + relativedelta(days=1),
                    'request_date_to': date.today() + relativedelta(days=2),
                    'employee_id': self.employee_emp_id,
                })
                self.assertFalse(
                    any('New Time Off Request' in m.subject for m in self._new_mails),
                    "No officer notification should be sent when disabled",
                )
