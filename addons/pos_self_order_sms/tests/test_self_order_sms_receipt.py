# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged('post_install', '-at_install')
class TestPosSelfOrderSms(SelfOrderCommonTest):

    def test_sms_receipt_sent_for_self_order(self):
        self.out_preset.sms_receipt_template_id = self.env.ref('pos_sms.sms_template_data_point_of_sale')
        self.pos_config.open_ui()
        order = self.env['pos.order'].create({
            'source': 'mobile',
            'config_id': self.pos_config.id,
            'session_id': self.pos_config.current_session_id.id,
            'company_id': self.pos_config.company_id.id,
            'amount_total': 2.20,
            'amount_paid': 2.20,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'preset_id': self.out_preset.id,
            'pos_reference': '1000-004-00001',
            'name': 'Order 1001',
            'state': 'draft',
            'mobile': '+1 (307) 410-6456',
            'lines': [(0, 0, {
                'product_id': self.cola.id,
                'price_unit': 2.2,
                'qty': 1,
                'tax_ids': False,
                'price_subtotal': 2.20,
                'price_subtotal_incl': 2.20,
            })],
        })

        payment_context = {"active_id": order.id, "active_ids": order.ids}
        self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': 2.20,
            'payment_method_id': self.bank_payment_method.id,
        }).check()

        self.assertTrue(order.preset_id.sms_receipt_template_id)
        self.assertEqual(
            len(order.message_ids.filtered(lambda m: m.message_type == 'sms')),
            1,
            'An SMS confirmation should be sent to the customer when a self-order is paid.',
        )
