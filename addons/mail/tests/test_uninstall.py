# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, TransactionCase


@tagged('-at_install', 'post_install')
class TestMailUninstall(TransactionCase):
    def test_unlink_model(self):
        model = self.env['ir.model'].create({
            'name': 'Test Model',
            'model': 'x_test_model',
            'state': 'manual',
            'is_mail_thread': True,
        })
        activity_type = self.env['mail.activity.type'].create({
            'name': 'Test Activity Type',
            'res_model': model.model,
        })
        record = self.env[model.model].create({})

        activity = self.env['mail.activity'].create({
            'activity_type_id': activity_type.id,
            'res_model_id': model.id,
            'res_id': record.id,
        })

        model.unlink()
        self.assertFalse(model.exists())
        self.assertFalse(activity_type.exists())
        self.assertFalse(activity.exists())
