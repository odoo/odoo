# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleAutoInvoice(WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Controller = WebsiteSale()

    def test_automatic_invoice_on_zero_amount(self):
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')

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
            }
        )

        self.cart.carrier_id = self.free_delivery

        # Apply discount
        self.cart._try_apply_code("100code")
        self.cart._apply_program_reward(program.reward_ids, program.coupon_ids)

        with MockRequest(self.env, sale_order_id=self.cart.id, website=self.website):
            self.Controller.shop_payment_validate()
        self.assertTrue(
            self.cart.invoice_ids, "Invoices should be generated for orders with zero total amount",
        )
