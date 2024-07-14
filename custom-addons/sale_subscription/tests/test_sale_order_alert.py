
# -*- coding: utf-8 -*-

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestSaleOrderAlert(TestSubscriptionCommon):
    def test_save_template_sale_order_alert(self):

        sale_order_model_id = self.env['ir.model']._get_id('sale.order')
        mail_template = self.env['mail.template'].create({
            'lang': '{{ object.lang }}',
            'model_id': sale_order_model_id,
            'name': 'Test template',
            'partner_to': '{{ object.id }}',
        })
        alert = self.env['sale.order.alert'].create({
            'name': 'Test Alert',
            'trigger_condition': 'on_create_or_write',
            'mrr_min': 0,
            'mrr_max': 80,
            'action': 'mail_post',
            'template_id': mail_template.id,
            'model_id': sale_order_model_id,
        })
        self.assertEqual(alert.template_id.id, mail_template.id, "The template should be saved.")

    def test_update_sale_order_alert(self):

        sale_order_model_id = self.env['ir.model']._get_id('sale.order')
        mail_template = self.env['mail.template'].create({
            'lang': '{{ object.lang }}',
            'model_id': sale_order_model_id,
            'name': 'Test template',
            'partner_to': '{{ object.id }}',
        })
        alert = self.env['sale.order.alert'].create({
            'name': 'Test Alert',
            'trigger_condition': 'on_create_or_write',
            'mrr_min': 0,
            'mrr_max': 80,
            'action': 'mail_post',
            'template_id': mail_template.id,
            'model_id': sale_order_model_id,
        })

        alert.subscription_state_from = '3_progress'
        self.assertEqual(alert.subscription_state_from, '3_progress', "The update should be saved.")
