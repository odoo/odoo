
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

    def test_alert_stage_change(self):
        """
        Check that a sale order alert generates exactly one activity when the state of a subscription changes
        from the `from` state to the `to` state defined in the alert and one of the two fields is left empty.
        In that case, an alert should only be generated once, when the non-empty state is left/reached.
        """
        subscription = self.subscription
        alert = self.env['sale.order.alert'].create([{
            'name': 'Activity when a subscription reaches Progress state',
            'trigger_condition': 'on_create_or_write',
            'action': 'next_activity',
            'activity_user': 'contract',
            'subscription_state': '3_progress',
        }])
        alert.activity_type_id = self.env['mail.activity.type'].search([('name', '=', 'Email')])

        activity_count = len(subscription.activity_ids)
        subscription.internal_note = "trigger a write on the subscription"
        self.assertEqual(len(subscription.activity_ids), activity_count)

        subscription.action_confirm()
        self.assertEqual(len(subscription.activity_ids), activity_count + 1)

        # Change alert to check pre_domain and domain of automation are correctly updated
        alert.subscription_state_from = '3_progress'
        alert.subscription_state = False

        subscription.action_draft()
        self.assertEqual(len(subscription.activity_ids), activity_count + 2)
