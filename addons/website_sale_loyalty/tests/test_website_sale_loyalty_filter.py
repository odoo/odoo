# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWebsiteSaleLoyaltyFilter(TransactionCase):

    def test_filter_irrelevant_global_discounts(self):
        program = self.env['loyalty.program'].create({
            'name': 'Global Promotions',
            'program_type': 'promo_code',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [
                Command.create({
                    'mode': 'with_code',
                    'code': '12345',
                    'reward_point_amount': 400,
                }),
            ],
            'reward_ids': [
                Command.create({
                    'discount_applicability': 'order',
                    'required_points': 100,
                    'reward_type': 'discount',
                    'discount': 10,
                }),
                Command.create({
                    'discount_applicability': 'order',
                    'required_points': 200,
                    'reward_type': 'discount',
                    'discount': 20,
                }),
                Command.create({
                    'discount_applicability': 'order',
                    'required_points': 300,
                    'reward_type': 'discount',
                    'discount': 30,
                }),
            ],
        })

        irrelevant_rewards = program.reward_ids[:2]
        really_good_reward = program.reward_ids[2]

        product = self.env['product.product'].create({
            'name': "Some amazing product",
            'list_price': 100,
        })

        partner = self.env['res.partner'].create({
            'name': 'Test Partner',
        })

        order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [
                Command.create({
                    'product_id': product.id,
                }),
            ]
        })

        order._try_apply_code('12345')
        res = order._get_claimable_and_showable_rewards()
        all_rewards = self.env['loyalty.reward']
        for reward in res.values():
            all_rewards |= reward

        self.assertIn(really_good_reward, all_rewards, "The best reward should be accessible to the customer")
        self.assertFalse(bool(all_rewards & irrelevant_rewards), "The lesser attractive rewards should be filtered out")

    def test_dont_filter_other_type_of_discount(self):
        test_product = self.env['product.product'].create({
            'name': "Test Product",
            'list_price': 1234,
        })
        cheap_product = self.env['product.product'].create({
            'name': "Cheap Product",
            'list_price': 1,
        })

        global_program = self.env['loyalty.program'].create({
            'name': 'Global Promotions',
            'program_type': 'promotion',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [
                Command.create({
                    'reward_point_amount': 300,
                }),
            ],
            'reward_ids': [
                Command.create({
                    'discount_applicability': 'order',
                    'required_points': 100,
                    'reward_type': 'discount',
                    'discount': 10,
                }),
                Command.create({
                    'discount_applicability': 'order',
                    'required_points': 300,
                    'reward_type': 'discount',
                    'discount': 30,
                }),
            ],
        })
        specific_program = self.env['loyalty.program'].create({
            'name': '10% on Test Product',
            'program_type': 'promotion',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [
                Command.create({
                    'product_ids': test_product,
                    'reward_point_amount': 100,
                    'minimum_qty': 1,
                }),
            ],
            'reward_ids': [
                Command.create({
                    'discount_applicability': 'specific',
                    'required_points': 100,
                    'reward_type': 'discount',
                    'discount': 10,
                    'discount_product_ids': test_product,
                }),
            ],
        })
        cheapest_program = self.env['loyalty.program'].create({
            'name': '10% on Cheapest Product',
            'program_type': 'promotion',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [
                Command.create({
                    'product_ids': cheap_product,
                    'minimum_qty': 1,
                    'reward_point_amount': 100,
                }),
            ],
            'reward_ids': [
                Command.create({
                    'discount_applicability': 'cheapest',
                    'required_points': 100,
                    'reward_type': 'discount',
                    'discount': 10,
                }),
            ],
        })

        specific_reward = specific_program.reward_ids
        cheapest_reward = cheapest_program.reward_ids
        other_type_rewards = specific_reward | cheapest_reward
        irrelevant_reward = global_program.reward_ids[0]
        really_good_reward = global_program.reward_ids[1]

        partner = self.env['res.partner'].create({
            'name': 'Test Partner',
        })

        order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [
                Command.create({
                    'product_id': test_product.id,
                }),
                Command.create({
                    'product_id': cheap_product.id,
                }),
            ]
        })
        order._update_programs_and_rewards()

        res = order._get_claimable_and_showable_rewards()
        all_rewards = self.env['loyalty.reward']
        for reward in res.values():
            all_rewards |= reward

        self.assertIn(really_good_reward, all_rewards, "The best reward should be accessible to the customer")
        self.assertTrue(other_type_rewards <= all_rewards, "The other types of reward should not be touched")
        self.assertTrue(irrelevant_reward not in all_rewards, "The lesser attractive reward should be filtered out")
