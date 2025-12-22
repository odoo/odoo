# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, http
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_loyalty.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class TestFreeProductReward(HttpCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.WebsiteSaleController = WebsiteSale()
        cls.website = cls.env.ref('website.default_website').with_user(cls.user_demo)

        cls.sofa, cls.carpet = cls.env['product.product'].create([
            {
                'name': "Test Sofa",
                'list_price': 2950.0,
                'website_published': True,
            },
            {
                'name': "Test Carpet",
                'list_price': 500.0,
                'website_published': True,
            },
        ])

        # Disable any other program
        cls.program = cls.env['loyalty.program'].search([]).write({'active': False})

        cls.program = cls.env['loyalty.program'].create({
            'name': 'Get a product for free',
            'program_type': 'promotion',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'minimum_qty': 1,
                'minimum_amount': 0.00,
                'reward_point_amount': 1,
                'reward_point_mode': 'order',
                'product_ids': cls.sofa,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': cls.carpet.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        })

        cls.empty_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_demo.id,
        })

        installed_modules = set(cls.env['ir.module.module'].search([
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

    def test_get_claimable_free_shipping(self):
        order = self.empty_order
        self.program.write({
            'program_type': 'next_order_coupons',
            'applies_on': 'future',
            'coupon_ids': [Command.create({'partner_id': order.partner_id.id, 'points': 100})],
            'reward_ids': [Command.update(self.program.reward_ids.id, {
                'reward_type': 'shipping',
                'reward_product_id': None,
            })],
        })
        coupon = self.program.coupon_ids

        with MockRequest(self.website.env, website=self.website, sale_order_id=order.id):
            self.assertDictEqual(order._get_claimable_and_showable_rewards(), {
                coupon: self.program.reward_ids,
            })
            self.WebsiteSaleController.cart_update_json(self.sofa.id, set_qty=1)
            self.WebsiteSaleController.claim_reward(self.program.reward_ids.id, code=coupon.code)
            self.assertFalse(
                order._get_claimable_and_showable_rewards(),
                "Rewards should no longer be claimable if already claimed",
            )
