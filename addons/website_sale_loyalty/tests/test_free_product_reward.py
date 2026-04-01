# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, http
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon
from odoo.addons.website_sale_loyalty.controllers.cart import Cart
from odoo.addons.website_sale_loyalty.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class TestFreeProductReward(HttpCaseWithUserPortal, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.WebsiteSaleCartController = Cart()
        cls.WebsiteSaleController = WebsiteSale()

        cls.website = cls.website.with_user(cls.user_portal)
        cls.empty_cart.partner_id = cls.partner_portal

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
            'rule_ids': [Command.create({
                'minimum_qty': 1,
                'minimum_amount': 0.00,
                'reward_point_amount': 1,
                'reward_point_mode': 'order',
                'product_ids': cls.sofa,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'product',
                'reward_product_id': cls.carpet.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        })

        installed_modules = cls.env['ir.module.module'].search([('state', '=', 'installed')])
        for _ in http._generate_routing_rules(installed_modules.mapped('name'), nodb_only=False):
            pass

    def test_add_product_to_cart_when_it_exist_as_free_product(self):
        # This test the flow when we claim a reward in the cart page and then we
        # want to add the product again
        order = self.empty_cart
        with MockRequest(self.website.env, website=self.website, sale_order_id=order.id):
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=self.sofa.product_tmpl_id,
                product_id=self.sofa.id,
                quantity=1,
            )
            self.WebsiteSaleController.claim_reward(self.program.reward_ids[0].id)
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=self.carpet.product_tmpl_id,
                product_id=self.carpet.id,
                quantity=1,
            )
            sofa_line = order.order_line.filtered(lambda line: line.product_id.id == self.sofa.id)
            carpet_reward_line = order.order_line.filtered(lambda line: line.product_id.id == self.carpet.id and line.is_reward_line)
            carpet_line = order.order_line.filtered(lambda line: line.product_id.id == self.carpet.id and not line.is_reward_line)
            self.assertEqual(sofa_line.product_uom_qty, 1, "Should have only 1 qty of Sofa")
            self.assertEqual(carpet_reward_line.product_uom_qty, 1, "Should have only 1 qty for the carpet as reward")
            self.assertEqual(carpet_line.product_uom_qty, 1, "Should have only 1 qty for carpet as non reward")

    def test_get_claimable_free_shipping(self):
        cart = self.empty_cart
        self.program.write({
            'program_type': 'next_order_coupons',
            'applies_on': 'future',
            'coupon_ids': [
                Command.clear(),
                Command.create({'partner_id': cart.partner_id.id, 'points': 100}),
            ],
            'reward_ids': [Command.update(self.program.reward_ids.id, {
                'reward_type': 'shipping',
                'reward_product_id': None,
            })],
        })
        coupon = self.program.coupon_ids

        with MockRequest(self.website.env, website=self.website, sale_order_id=cart.id):
            self.assertDictEqual(cart._get_claimable_and_showable_rewards(), {
                coupon: self.program.reward_ids,
            })
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=self.sofa.product_tmpl_id,
                product_id=self.sofa.id,
                quantity=1,
            )
            self.WebsiteSaleController.claim_reward(self.program.reward_ids.id, code=coupon.code)
            self.assertTrue(cart.order_line.reward_id)
            self.assertFalse(
                cart._get_claimable_and_showable_rewards(),
                "Rewards should no longer be claimable if already claimed",
            )
