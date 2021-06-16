# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.exceptions import ValidationError
from odoo.fields import Command
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestLoyalty(TransactionCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super(TestLoyalty, cls).setUpClass()
        cls.partner_id = cls.env['res.partner'].create({'name': 'My Test Customer'})
        cls.product_gift = cls.env['product.product'].create({'name': 'Gift'})
        cls.reward_id = cls.env['loyalty.reward'].create({
            'name': 'Gift',
            'reward_type': 'product',
            'point_cost': 5,
            'reward_product_id': cls.product_gift.id,
        })
        cls.product_1 = cls.env['product.product'].create({'name': 'Product one'})
        cls.product_2 = cls.env['product.product'].create({'name': 'Product two'})

    def setUp(self):
        super().setUp()
        # Mock this method because no actual request is used to perform the test
        def is_public_user(*args, **kwargs):
            return False
        patcher = patch('odoo.addons.website.models.website.Website.is_public_user', wraps=is_public_user)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_loyalty(self):
        loyalty_id = self.env['loyalty.program'].create({
            'name': 'Test Program',
            'points': 0.01,
            'reward_ids': [Command.set([self.reward_id.id])]
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [Command.create({
                'name': self.product_1.name,
                'product_id': self.product_1.id,
                'product_uom_qty': 2,
                'price_unit': 750.00,
            })],
        })

        sale_order.recompute_loyalty_points(loyalty_id.id)

        self.assertRecordValues(sale_order, [
            {'won_loyalty_points': 17, 'spent_loyalty_points': 0},
        ])

        self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'name': self.product_gift.name,
            'product_id': self.product_gift.id,
            'product_uom_qty': 1,
            'price_unit': 0,
            'loyalty_reward_id': self.reward_id.id,
            'is_main_loyalty_reward': True,
        })

        sale_order.recompute_loyalty_points(loyalty_id.id)

        self.assertRecordValues(sale_order, [
            {'won_loyalty_points': 17, 'spent_loyalty_points': 5},
        ])

    def test_loyalty_rule(self):
        loyalty_id = self.env['loyalty.program'].create({
            'name': 'Test Program with rules',
            'points': 0.00,
            'reward_ids': [Command.set([self.reward_id.id])],
            'rule_ids': [
                Command.create({
                    'name': 'Rule one',
                    'points_quantity': 10.0,
                    'points_currency': 0,
                    'rule_domain': "[('name', '=', 'Product one')]",
                }),
                Command.create({
                    'name': 'Rule two',
                    'points_quantity': 0,
                    'points_currency': 0.2,
                    'rule_domain': "[('name', '=', 'Product two')]",
                }),
            ]
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [Command.create({
                'name': self.product_1.name,
                'product_id': self.product_1.id,
                'product_uom_qty': 7,
                'price_unit': 100.00,
            })],
        })
        sale_order.recompute_loyalty_points(loyalty_id.id)
        self.assertRecordValues(sale_order, [
            {'won_loyalty_points': 70, 'spent_loyalty_points': 0},
        ])

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [Command.create({
                'name': self.product_2.name,
                'product_id': self.product_2.id,
                'product_uom_qty': 2,
                'price_unit': 150.00,
            })],
        })
        # total price = (2*150)+tax = 300+15% = 345
        sale_order.recompute_loyalty_points(loyalty_id.id)
        self.assertRecordValues(sale_order, [
            {'won_loyalty_points': 69, 'spent_loyalty_points': 0},
        ])

    def test_negative_balance_immediate_payment(self):
        """Fail when spending more points than available on immediate payment"""
        order_line = [Command.create({
            'name': self.product_1.name,
            'product_id': self.product_1.id,
            'product_uom_qty': 1,
            'price_unit': 100.00,
        })]
        with self.assertRaises(ValidationError, msg="Loyalty points cannot be negative"):
            sale_order = self.env['sale.order'].create({
                'partner_id': self.partner_id.id,
                'order_line': order_line,
                'won_loyalty_points': 0,
                'spent_loyalty_points': 1,
            })
            sale_order.state = 'sale'

    def test_negative_balance_differed_payment(self):
        """Fail when spending more points than available on differed payment"""
        order_line = [Command.create({
            'name': self.product_1.name,
            'product_id': self.product_1.id,
            'product_uom_qty': 1,
            'price_unit': 100.00,
        })]
        with self.assertRaises(ValidationError, msg="Loyalty points cannot be negative"):
            sale_order = self.env['sale.order'].create({
                'partner_id': self.partner_id.id,
                'order_line': order_line,
                'won_loyalty_points': 0,
                'spent_loyalty_points': 1,
            })
            sale_order.state = 'sent'

    def test_loyalty_balance(self):
        order_line = [Command.create({
            'name': self.product_1.name,
            'product_id': self.product_1.id,
            'product_uom_qty': 1,
            'price_unit': 100.00,
        })]

        # immediate payment get points
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': order_line,
            'won_loyalty_points': 100,
            'spent_loyalty_points': 0,
        })
        self.assertEqual(self.partner_id.loyalty_points, 0)
        sale_order.state = 'sale'
        self.assertEqual(self.partner_id.loyalty_points, 100)

        # immediate payment get and spend points
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': order_line,
            'won_loyalty_points': 100,
            'spent_loyalty_points': 10,
        })
        self.assertEqual(self.partner_id.loyalty_points, 100)
        sale_order.state = 'sale'
        self.assertEqual(self.partner_id.loyalty_points, 190)
        sale_order.state = 'cancel'
        self.assertEqual(self.partner_id.loyalty_points, 100)

        # delayed payment get and spend points
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': order_line,
            'won_loyalty_points': 100,
            'spent_loyalty_points': 10,
        })
        self.assertEqual(self.partner_id.loyalty_points, 100)
        sale_order.state = 'sent'
        self.assertEqual(self.partner_id.loyalty_points, 90)
        sale_order.state = 'sale'
        self.assertEqual(self.partner_id.loyalty_points, 190)
        sale_order.state = 'cancel'
        self.assertEqual(self.partner_id.loyalty_points, 100)

    def test_discount(self):
        loyalty_id = self.env['loyalty.program'].create({
            'name': 'Test Program',
            'points': 0.01,
        })

        self.partner_id.loyalty_points = 1000  # reward must be affordable
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [Command.create({
                'name': self.product_1.name,
                'product_id': self.product_1.id,
                'product_uom_qty': 1,
                'price_unit': 100.00,
            })],
        })

        # fixed amount discount
        reward_id = self.env['loyalty.reward'].create({
            'name': '-20 Discount',
            'reward_type': 'discount',
            'point_cost': 100,
            'discount_type': 'fixed_amount',
            'discount_fixed_amount': 20,
            'loyalty_program_id': loyalty_id.id,
        })
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.amount_total, 115)  # 100+15%
        sale_order._cart_update_reward(reward_id.id, 1)
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 95)  # (100+15%)-20)
        sale_order._cart_update(reward_id.discount_product_id.id, add_qty=-1, line_id=sale_order.order_line[1].id)
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.amount_total, 115)  # 100+15%

        # percentage amount discount on full order
        reward_id = self.env['loyalty.reward'].create({
            'name': '10% Discount',
            'reward_type': 'discount',
            'point_cost': 100,
            'discount_type': 'percentage',
            'discount_percentage': 10,
            'discount_apply_on': 'on_order',
            'loyalty_program_id': loyalty_id.id,
        })
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.amount_total, 115)  # 100+15%
        sale_order._cart_update_reward(reward_id.id, 1)
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 103.5)  # (100+15%)-11.5
        sale_order._cart_update(reward_id.discount_product_id.id, add_qty=-1, line_id=sale_order.order_line[1].id)
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.amount_total, 115)  # 100+15%

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [Command.create({
                'name': self.product_1.name,
                'product_id': self.product_1.id,
                'product_uom_qty': 2,
                'price_unit': 100.00,
            }), Command.create({
                'name': self.product_2.name,
                'product_id': self.product_2.id,
                'product_uom_qty': 3,
                'price_unit': 50.00,
            })],
        })

        # percentage amount discount on cheapest
        reward_id = self.env['loyalty.reward'].create({
            'name': '10% Discount',
            'reward_type': 'discount',
            'point_cost': 100,
            'discount_type': 'percentage',
            'discount_percentage': 10,
            'discount_apply_on': 'cheapest_product',
            'loyalty_program_id': loyalty_id.id,
        })
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 402.5)  # (2*100+3*50)+15% = 350+15%
        sale_order._cart_update_reward(reward_id.id, 1)
        self.assertEqual(len(sale_order.order_line), 3)
        self.assertEqual(sale_order.amount_total, 396.75)  # (2*100+3*50-5)+15% = 345+15%
        sale_order._cart_update(reward_id.discount_product_id.id, add_qty=-1, line_id=sale_order.order_line[2].id)
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 402.5)  # (2*100+3*50)+15% = 350+15%

        # percentage amount discount on specific product
        reward_id = self.env['loyalty.reward'].create({
            'name': '10% Discount',
            'reward_type': 'discount',
            'point_cost': 100,
            'discount_type': 'percentage',
            'discount_percentage': 10,
            'discount_apply_on': 'specific_products',
            'discount_specific_product_ids': [self.product_1.id],
            'loyalty_program_id': loyalty_id.id,
        })
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 402.5)  # (2*100+3*50)+15% = 350+15%
        sale_order._cart_update_reward(reward_id.id, 1)
        self.assertEqual(len(sale_order.order_line), 3)
        self.assertEqual(sale_order.amount_total, 379.5)  # (2*(100-10)+3*50)+15% = 330+15%
        sale_order._cart_update(reward_id.discount_product_id.id, add_qty=-1, line_id=sale_order.order_line[2].id)
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 402.5)  # (2*100+3*50)+15% = 350+15%

    def test_discount_with_taxes(self):
        loyalty_id = self.env['loyalty.program'].create({
            'name': 'Test Program',
            'points': 0.01,
        })
        tax_15 = self.env['account.tax'].create({
            'name': 'tax_15',
            'amount_type': 'percent',
            'amount': 15,
            'type_tax_use': 'sale',
        })
        tax_25 = self.env['account.tax'].create({
            'name': 'tax_25',
            'amount_type': 'percent',
            'amount': 25,
            'type_tax_use': 'sale',
        })

        self.partner_id.loyalty_points = 1000  # reward must be affordable
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [Command.create({
                'name': self.product_1.name,
                'product_id': self.product_1.id,
                'product_uom_qty': 1,
                'price_unit': 100.00,
                'tax_id': tax_15,
            })],
        })

        # fixed amount discount
        reward_id = self.env['loyalty.reward'].create({
            'name': '-20 Discount',
            'reward_type': 'discount',
            'point_cost': 100,
            'discount_type': 'fixed_amount',
            'discount_fixed_amount': 20,
            'loyalty_program_id': loyalty_id.id,
        })
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.amount_total, 115)  # 100+15%
        sale_order._cart_update_reward(reward_id.id, 1)
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 95)  # (100+15%)-20
        sale_order._cart_update(reward_id.discount_product_id.id, add_qty=-1, line_id=sale_order.order_line[1].id)
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.amount_total, 115)  # 100+15%

        # percentage amount discount on full order
        reward_id = self.env['loyalty.reward'].create({
            'name': '10% Discount',
            'reward_type': 'discount',
            'point_cost': 100,
            'discount_type': 'percentage',
            'discount_percentage': 10,
            'discount_apply_on': 'on_order',
            'loyalty_program_id': loyalty_id.id,
        })
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.amount_total, 115)  # 100+15%
        sale_order._cart_update_reward(reward_id.id, 1)
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 103.5)  # (100+15%)-11.5
        sale_order._cart_update(reward_id.discount_product_id.id, add_qty=-1, line_id=sale_order.order_line[1].id)
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.amount_total, 115)  # 100+15%

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [Command.create({
                'name': self.product_1.name,
                'product_id': self.product_1.id,
                'product_uom_qty': 2,
                'price_unit': 100.00,
                'tax_id': tax_15,
            }), Command.create({
                'name': self.product_2.name,
                'product_id': self.product_2.id,
                'product_uom_qty': 3,
                'price_unit': 50.00,
                'tax_id': tax_25,
            })],
        })

        # percentage amount discount on order
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 417.5)  # (2*100)+15%+(3*50)+25% = 200+15% + 150+25%
        sale_order._cart_update_reward(reward_id.id, 1)
        self.assertEqual(len(sale_order.order_line), 5)  # 2 products + 1 reward for points + 2 discounts
        self.assertEqual(len(sale_order.website_order_line), 3)  # 2 products + 1 reward
        self.assertEqual(sale_order.amount_total, 375.75)  # 2*(100-10)+15%+3*(50-10%)+25%
        sale_order._cart_update(reward_id.discount_product_id.id, add_qty=-1, line_id=sale_order.order_line[2].id)
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 417.5)  # (2*100)+15%+(3*50)+25% = 200+15% + 150+25%

        # percentage amount discount on cheapest
        reward_id = self.env['loyalty.reward'].create({
            'name': '10% Discount',
            'reward_type': 'discount',
            'point_cost': 100,
            'discount_type': 'percentage',
            'discount_percentage': 10,
            'discount_apply_on': 'cheapest_product',
            'loyalty_program_id': loyalty_id.id,
        })
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 417.5)  # (2*100)+15%+(3*50)+25% = 200+15% + 150+25%
        sale_order._cart_update_reward(reward_id.id, 1)
        self.assertEqual(len(sale_order.order_line), 3)
        self.assertEqual(sale_order.amount_total, 411.25)  # (2*100)+15%+(3*50-5)+25% = 230 + 181.25
        sale_order._cart_update(reward_id.discount_product_id.id, add_qty=-1, line_id=sale_order.order_line[2].id)
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 417.5)  # (2*100)+15%+(3*50)+25% = 200+15% + 150+25%

        # percentage amount discount on specific product
        reward_id = self.env['loyalty.reward'].create({
            'name': '10% Discount',
            'reward_type': 'discount',
            'point_cost': 100,
            'discount_type': 'percentage',
            'discount_percentage': 10,
            'discount_apply_on': 'specific_products',
            'discount_specific_product_ids': [self.product_1.id],
            'loyalty_program_id': loyalty_id.id,
        })
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 417.5)  # (2*100)+15%+(3*50)+25% = 200+15% + 150+25%
        sale_order._cart_update_reward(reward_id.id, 1)
        self.assertEqual(len(sale_order.order_line), 3)
        self.assertEqual(sale_order.amount_total, 394.5)  # (2*(100-10)+15%)+(3*50+25%) = 207+187.5
        sale_order._cart_update(reward_id.discount_product_id.id, add_qty=-1, line_id=sale_order.order_line[2].id)
        self.assertEqual(len(sale_order.order_line), 2)
        self.assertEqual(sale_order.amount_total, 417.5)  # (2*100)+15%+(3*50)+25% = 200+15% + 150+25%
