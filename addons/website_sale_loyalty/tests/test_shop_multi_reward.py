# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon
from odoo.addons.website_sale_loyalty.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class TestClaimReward(WebsiteSaleCommon):

    def test_claim_reward_with_multi_product(self):
        WebsiteSaleController = WebsiteSale()

        tag = self.env['product.tag'].create({
            'name': 'multi reward',
        })

        product1, product2 = self.env['product.product'].create([
            {
            'name': 'Test Product',
            'list_price': 10.0,
            'product_tag_ids': tag,
        }, {
            'name': 'Test Product 2',
            'list_price': 20.0,
            'product_tag_ids': tag,
        }])

        promo_program = self.env['loyalty.program'].create({
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
            })]
        })

        order = self.empty_cart
        order.order_line = [Command.create({'product_id': product1.id})]
        order._update_programs_and_rewards()
        with MockRequest(self.env, website=self.website, sale_order_id=order.id):
            WebsiteSaleController.claim_reward(promo_program.reward_ids[:1].id, product_id=str(product2.id))

            self.assertEqual(len(order.order_line), 2, 'reward line should be added to order')
            self.assertEqual(order.order_line[1].product_id, product2, 'added reward line should should contain product 2')
