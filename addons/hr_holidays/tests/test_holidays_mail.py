# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import date
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo.tools import mute_logger

from .common import TestHrHolidaysCommon
from odoo.tests import tagged

from odoo.addons.mail.tests.common import MailCase


class TestHolidaysMail(TestHrHolidaysCommon, MailCase):
    """Test that mails are correctly sent when a timeoff is taken"""

    @mute_logger('odoo.addons.base.models.ir_access', 'odoo.models')
    def test_email_sent_when_approved(self):
        """ Testing leave request flow: limited type of leave request """
        with freeze_time('2022-01-15'):
            self.admin_employee.tz = "Europe/Brussels"

            time_type_paid_time_off = self.env['hr.time.type'].create({
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
                    'time_type_id': time_type_paid_time_off.id,
                    'number_of_days': 20,
                    'employee_id': self.employee_emp_id,
                    'state': 'confirm',
                    'date_from': time.strftime('%Y-%m-01'),
                }
            ])

            self.env['hr.leave.allocation'].create([
                {
                    'name': 'Paid Time off for Mitchell',
                    'time_type_id': time_type_paid_time_off.id,
                    'number_of_days': 20,
                    'employee_id': self.admin_employee.id,
                    'state': 'confirm',
                    'date_from': time.strftime('%Y-%m-01'),
                },
            ])

            leave_vals = {
                'name': 'Sick Time Off',
                'time_type_id': time_type_paid_time_off.id,
                'request_date_from': date.today() + relativedelta(day=2),
                'request_date_to': date.today() + relativedelta(day=3),
                'employee_id': self.admin_employee.id,
            }
            leave = self.env['hr.leave'].create(leave_vals)
            leave.action_approve()
            with self.mock_mail_gateway():
                leave.action_approve()
                admin_emails = self._new_mails.filtered(lambda x: self.admin_employee in x.partner_ids.employee_ids)
                self.assertEqual(len(admin_emails), 1, "Mitchell Admin should receive an email")
                self.assertTrue("has been accepted" in admin_emails.preview)

    def test_refuse_cancel_notification_model_description(self):
        """ The approvers notified of a refusal or a cancellation get the model description """
        time_type = self.env['hr.time.type'].create({
            'name': 'Manager Time Off',
            'code': 'Manager Time Off',
            'requires_allocation': False,
            'leave_validation_type': 'manager',
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        leaves = self.env['hr.leave'].create([{
            'name': 'Time Off',
            'time_type_id': time_type.id,
            'request_date_from': day,
            'request_date_to': day,
            'employee_id': self.employee_emp_id,
        } for day in (date(2030, 1, 7), date(2030, 1, 8))])
        self.assertEqual(leaves.mapped('state'), ['validate', 'validate'])
        with patch.object(self.registry['hr.leave'], 'message_notify', autospec=True) as message_notify:
            leaves[0].action_refuse()
            leaves[1]._force_cancel('No longer needed')
        self.assertEqual(
            [call.kwargs['model_description'] for call in message_notify.call_args_list],
            ['Time Off', 'Time Off'],
        )
