# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.tests import tagged, TransactionCase


@tagged('-at_install', 'post_install')
class TestHrLeaveUninstall(TransactionCase):
    def test_unlink_model(self):
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee'
        })
        holiday = self.env['hr.leave'].create({
            'name': 'Time Off',
            'employee_id': employee.id,
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_sl').id,
            'request_date_from': date(2020, 1, 7),
            'date_from': date(2020, 1, 7),
            'request_date_to': date(2020, 1, 9),
            'date_to': date(2020, 1, 9),
            'number_of_days': 3,
        })
        holiday.activity_schedule(
            'hr_holidays.mail_act_leave_approval',
            note='Test Note',
            user_id=self.env.user.id)
        model = self.env['ir.model'].search([('model', '=', 'hr.leave')])
        activity_type = self.env['mail.activity'].search([
            ('res_model', '=', 'hr.leave')
        ]).activity_type_id

        self.assertTrue(activity_type)
        self.assertIn('hr.leave', activity_type.mapped('res_model'))

        model.sudo().with_context(**{MODULE_UNINSTALL_FLAG: True}).unlink()
        self.assertFalse(model.exists())

        domain = [('res_model', '=', 'hr.leave')]
        self.assertFalse(self.env['mail.activity'].search(domain))
        self.assertFalse(self.env['mail.activity.type'].search(domain))
        self.assertFalse(self.env['mail.followers'].search(domain))
        self.assertFalse(self.env['mail.message'].search([
            ('model', '=', 'hr.leave'),
        ]))
