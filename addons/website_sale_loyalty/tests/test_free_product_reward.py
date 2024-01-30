# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.tests.common import HttpCase
from odoo.tests import tagged
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_loyalty.controllers.main import WebsiteSale

@tagged('post_install', '-at_install')
class TestFreeProductReward(HttpCase):

    def setUp(self):
        super().setUp()

        self.WebsiteSaleController = WebsiteSale()
        self.website = self.env['website'].browse(1)

        self.sofa = self.env['product.product'].create({
            'name': 'Test Sofa',
            'list_price': 2950.0,
            'website_published': True,
        })

        self.carpet = self.env['product.product'].create({
            'name': 'Test Carpet',
            'list_price': 500.0,
            'website_published': True,
        })

        # Disable any other program
        self.program = self.env['loyalty.program'].search([]).write({'active': False})

        self.program = self.env['loyalty.program'].create({
            'name': 'Get a product for free',
            'program_type': 'promotion',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'minimum_qty': 1,
                'minimum_amount': 0.00,
                'reward_point_amount': 1,
                'reward_point_mode': 'order',
                'product_ids': self.sofa,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.carpet.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        })

        self.steve = self.env['res.partner'].create({
            'name': 'Steve Bucknor',
            'email': 'steve.bucknor@example.com',
        })

        self.empty_order = self.env['sale.order'].create({
            'partner_id': self.steve.id
        })

        installed_modules = set(self.env['ir.module.module'].search([
            ('state', '=', 'installed'),
        ]).mapped('name'))
        for _ in http._generate_routing_rules(installed_modules, nodb_only=False):
            pass

    def test_add_product_to_cart_when_it_exist_as_free_product(self):
        # This test the flow when we claim a reward in the cart page and then we
        # want to add the product again
        order = self.empty_order
        with MockRequest(self.env, website=self.website, sale_order_id=order.id, website_sale_current_pl=1):
            self.WebsiteSaleController.cart_update_json(self.sofa.id, set_qty=1)
            self.WebsiteSaleController.claim_reward(self.program.reward_ids[0].id)
            self.WebsiteSaleController.cart_update_json(self.carpet.id, set_qty=1)
            sofa_line = order.order_line.filtered(lambda line: line.product_id.id == self.sofa.id)
            carpet_reward_line = order.order_line.filtered(lambda line: line.product_id.id == self.carpet.id and line.is_reward_line)
            carpet_line = order.order_line.filtered(lambda line: line.product_id.id == self.carpet.id and not line.is_reward_line)
            self.assertEqual(sofa_line.product_uom_qty, 1, "Should have only 1 qty of Sofa")
            self.assertEqual(carpet_reward_line.product_uom_qty, 1, "Should have only 1 qty for the carpet as reward")
            self.assertEqual(carpet_line.product_uom_qty, 1, "Should have only 1 qty for carpet as non reward")
