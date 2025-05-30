# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleAutoInvoice(WebsiteSaleCommon):

    def test_automatic_invoice_on_zero_amount(self):
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_bool('sale.automatic_invoice', True)
        Controller = WebsiteSale()

        # Create a discount code
        program = self.env['loyalty.program'].sudo().create({
            'name': '100discount',
            'program_type': 'promo_code',
            'rule_ids': [
                Command.create({
                    'code': "100code",
                    'minimum_amount': 0,
                })
            ],
            'reward_ids': [
                Command.create({
                    'discount': 100,
                })
            ]
        })

        self.cart._set_delivery_method(self.free_delivery)
        self.cart.partner_id.write(self.dummy_partner_address_values)

        # Apply discount
        self.cart._try_apply_code("100code")
        self.cart._apply_program_reward(program.reward_ids, program.coupon_ids)

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/payment/validate', sale_order_id=self.cart.id,
        ):
            Controller.shop_payment_validate()
        self.assertTrue(
            self.cart.invoice_ids, "Invoices should be generated for orders with zero total amount",
        )
