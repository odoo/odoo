# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, Command
from odoo.tests import tagged, HttpCase
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_loyalty.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon

@tagged('post_install', '-at_install')
class TestEwallet(HttpCase, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.WebsiteSaleController = WebsiteSale()
        cls.website = cls.env['website'].browse(1)

        cls.product.write({'taxes_id': [Command.clear()]})

        cls.topup = cls.env['product.product'].create({
            'name': 'Ewallet Top up',
            'list_price': 50.0,
            'website_published': True,
        })

        cls.ewallet_program = cls.env['loyalty.program'].create([{
            'name': 'E-wallet Card Program',
            'program_type': 'ewallet',
            'trigger': 'auto',
            'applies_on': 'future',
            'rule_ids': [Command.create({
                'reward_point_mode': 'money',
                'reward_point_amount': 10,
                'product_ids': cls.topup,
            })],
            'reward_ids': [Command.create({
                'discount_mode': 'per_point',
                'discount': 1,
                'discount_applicability': 'order',
            })],
        }])
        installed_modules = set(cls.env['ir.module.module'].search([
            ('state', '=', 'installed'),
        ]).mapped('name'))
        for _ in http._generate_routing_rules(installed_modules, nodb_only=False):
            pass

    def test_ewallet(self):
        self.env['loyalty.generate.wizard'].create({
            'program_id': self.ewallet_program.id,
            'coupon_qty': 1,
            'points_granted': 10,
        }).generate_coupons()

        self.ewallet_program.coupon_ids[0].partner_id = self.env.user.partner_id

        order = self.empty_cart
        with MockRequest(self.env, website=self.website, sale_order_id=order.id):
            self.WebsiteSaleController.cart_update_json(self.product.id, set_qty=1)
            self.assertEqual(order.amount_total, 20)
            self.WebsiteSaleController.claim_reward(self.ewallet_program.reward_ids[0].id)
            self.assertEqual(order.amount_total, 10)
