# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.tests import tagged, TransactionCase


@tagged('-at_install', 'post_install')
class TestHrLeaveUninstall(TransactionCase):
    def test_unlink_model(self):
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
