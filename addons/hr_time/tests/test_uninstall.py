# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestHrTimeUninstall(TransactionCase):
    def test_unlink_model(self):
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee'
        })
        holiday = self.env['hr.time'].create({
            'name': 'Time Off',
            'employee_id': employee.id,
            'work_entry_type_id': self.env.ref('hr_work_entry.generic_work_entry_type_sick_leave').id,
            'request_date_from': date(2020, 1, 7),
            'date_from': date(2020, 1, 7),
            'request_date_to': date(2020, 1, 9),
            'date_to': date(2020, 1, 9),
            'number_of_days': 3,
        })
        holiday.activity_schedule(
            'hr_time.mail_act_leave_approval',
            note='Test Note',
            user_id=self.env.user.id)
        model = self.env['ir.model'].search([('model', '=', 'hr.time')])
        activity_type = self.env['mail.activity'].search([
            ('res_model', '=', 'hr.time')
        ]).activity_type_id

        self.assertTrue(activity_type)
        self.assertIn('hr.time', activity_type.mapped('res_model'))

        model.sudo().with_context(force_delete=True).unlink()
        self.assertFalse(model.exists())

        domain = [('res_model', '=', 'hr.time')]
        self.assertFalse(self.env['mail.activity'].search(domain))
        self.assertFalse(self.env['mail.activity.type'].search(domain))
        self.assertFalse(self.env['mail.followers'].search(domain))
        self.assertFalse(self.env['mail.message'].search([
            ('model', '=', 'hr.time'),
        ]))
