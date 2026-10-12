from odoo import Command
from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestPaymentProvider(PaymentCommon, TestSaleCouponCommon):

    def test_payment_method_incompatibly_with_gift_cards(self):
        """ Test that the on site payment method is not proposed when the
        sale order has a gift card """
        if self.env['ir.module.module'].search([('name', '=', 'website_sale_collect')]).state != 'installed':
            return

        order = self.sale_order
        self.immediate_promotion_program.active = False
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_A.id,
                'name': 'Ordinary Product A',
                'product_uom_qty': 1.0,
            }),
            Command.create({
                'product_id': self.product_gift_card.id,
                'name': 'Gift Card Product',
                'product_uom_qty': 1.0,
            }),
        ]})
        order._update_programs_and_rewards()
        order.carrier_id = self.env.ref('website_sale_collect.carrier_pick_up_in_store')

        payment_provider = self.env.ref('website_sale_collect.payment_provider_on_site')
        compatible_providers = self.env['payment.provider'].sudo()._find_available_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=order.id
        )
        self.assertNotIn(payment_provider, compatible_providers)
