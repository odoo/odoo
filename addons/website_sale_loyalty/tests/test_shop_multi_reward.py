# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import Command, http
from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon
from odoo.addons.website_sale_loyalty.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class TestClaimReward(WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.WebsiteSaleController = WebsiteSale()

        cls.user_portal = cls._create_new_portal_user()
        cls.partner_portal = cls.user_portal.partner_id

        cls.env['product.pricelist'].search([]).action_archive()

        tag = cls.env['product.tag'].create({
            'name': 'multi reward',
        })
        cls.product1, cls.product2 = cls.env['product.product'].create([
            {
            'name': 'Test Product',
            'list_price': 10.0,
            'taxes_id': False,
            'product_tag_ids': tag,
        }, {
            'name': 'Test Product 2',
            'list_price': 20.0,
            'taxes_id': False,
            'product_tag_ids': tag,
        }])

        cls.promo_program, cls.coupon_program = cls.env['loyalty.program'].create([{
            'name': 'Free Products',
            'program_type': 'promotion',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [Command.create({
                'minimum_qty': 1,
                'minimum_amount': 0.00,
                'reward_point_amount': 3,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'product',
                'reward_product_tag_id': tag.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        }, {
            'name': "Multi-reward coupons",
            'program_type': 'coupons',
            'applies_on': 'current',
            'trigger': 'with_code',
            'reward_ids': [
                Command.create({
                    'reward_type': 'product',
                    'reward_product_tag_id': tag.id,
                    'reward_product_qty': 1,
                    'required_points': 1,
                    'discount': None,
                }),
                Command.create({
                    'reward_type': 'discount',
                    'discount': 10.0,
                    'discount_mode': 'percent',
                    'required_points': 1,
                }),
            ],
            'coupon_ids': [Command.create({'points': 1})],
        }])
        cls.coupon = cls.coupon_program.coupon_ids

        installed_modules = set(cls.env['ir.module.module'].search([
            ('state', '=', 'installed'),
        ]).mapped('name'))
        for _ in http._generate_routing_rules(installed_modules, nodb_only=False):
            pass

    def test_claim_reward_with_multi_products(self):
        product1, product2 = self.product2, self.product2
        order = self.empty_cart
        order.order_line = [Command.create({'product_id': product1.id})]
        order._update_programs_and_rewards()
        with MockRequest(self.env, website=self.website, sale_order_id=order.id):
            self.WebsiteSaleController.claim_reward(
                self.promo_program.reward_ids.id,
                product_id=str(product2.id),
            )
            self.assertEqual(len(order.order_line), 2, 'reward line should be added to order')
            self.assertEqual(order.order_line[1].product_id, product2, 'added reward line should should contain product 2')

    def test_apply_coupon_with_multiple_rewards_claim_discount(self):
        cart = self.empty_cart
        cart.update({
            'partner_id': self.partner_portal.id,
            'order_line': [Command.create({'product_id': self.product1.id})],
        })
        cart._update_programs_and_rewards()
        website = cart.website_id.with_user(self.user_portal)
        discount_reward = self.coupon_program.reward_ids.filtered('discount')

        with MockRequest(website.env, website=website, sale_order_id=cart.id):
            self.WebsiteSaleController.pricelist(promo=self.coupon.code)
            self.assertFalse(cart.order_line.reward_id)

            self.WebsiteSaleController.claim_reward(discount_reward.id, code=self.coupon.code)
            self.assertTrue(cart.order_line.reward_id)
            self.assertEqual(
                discount_reward, cart.order_line.reward_id,
                "Discount reward should be added to order",
            )
            self.assertAlmostEqual(
                cart.amount_untaxed, self.product1.list_price * 0.9,
                delta=cart.currency_id.rounding,
                msg="10% discount should be applied",
            )

    def test_apply_coupon_with_multiple_rewards_claim_multiproduct(self):
        cart = self.empty_cart
        cart.update({
            'partner_id': self.partner_portal.id,
            'order_line': [Command.create({'product_id': self.product1.id})],
        })
        cart._update_programs_and_rewards()
        website = cart.website_id.with_user(self.user_portal)
        multiproduct_reward = self.coupon_program.reward_ids.filtered('reward_product_tag_id')

        with MockRequest(website.env, website=website, sale_order_id=cart.id):
            self.WebsiteSaleController.pricelist(promo=self.coupon.code)
            self.assertFalse(cart.order_line.reward_id)

            self.WebsiteSaleController.claim_reward(
                multiproduct_reward.id,
                code=self.coupon.code,
                product_id=str(self.product1.id),
            )
            self.assertEqual(
                multiproduct_reward, cart.order_line.reward_id,
                "Product reward should be added",
            )
            self.assertIn(
                self.product1, cart.order_line.product_id,
                "Chosen reward product should be added to order",
            )
