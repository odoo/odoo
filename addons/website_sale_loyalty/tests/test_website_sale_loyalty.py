# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.exceptions import UserError
from odoo.fields import Command
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestLoyalty(TransactionCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super(TestLoyalty, cls).setUpClass()
        cls.partner_id = cls.env['res.partner'].create({'name': 'My Test Customer'})
        cls.product_gift_card = cls.env['product.product'].create({
            'name': 'Gift Card',
            'list_price': 50,
            'detailed_type': 'gift',
        })
        cls.reward_id = cls.env['loyalty.website.reward'].create({
            'name': 'Gift',
            'point_cost': 75,
            'gift_card_product_id': cls.product_gift_card.id,
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
        self.assertEqual(17, sale_order.won_loyalty_points)

        self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 1,
            'price_unit': 1000.0,
        })

        sale_order.recompute_loyalty_points(loyalty_id.id)
        self.assertEqual(29, sale_order.won_loyalty_points)

    def test_loyalty_rule(self):
        loyalty_id = self.env['loyalty.program'].create({
            'name': 'Test Program with rules',
            'points': 0.00,
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
        self.assertEqual(70, sale_order.won_loyalty_points)

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
        self.assertEqual(69, sale_order.won_loyalty_points)

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
        })
        self.assertEqual(self.partner_id.loyalty_points, 0)
        sale_order.state = 'sale'
        self.assertEqual(self.partner_id.loyalty_points, 100)

        # immediate payment get and spend points
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': order_line,
            'won_loyalty_points': 100,
        })
        self.assertEqual(self.partner_id.loyalty_points, 100)
        sale_order.state = 'sale'
        self.assertEqual(self.partner_id.loyalty_points, 200)
        sale_order.state = 'cancel'
        self.assertEqual(self.partner_id.loyalty_points, 100)

        # delayed payment get and spend points
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': order_line,
            'won_loyalty_points': 100,
        })
        self.assertEqual(self.partner_id.loyalty_points, 100)
        sale_order.state = 'sent'
        self.assertEqual(self.partner_id.loyalty_points, 100)
        sale_order.state = 'sale'
        self.assertEqual(self.partner_id.loyalty_points, 200)
        sale_order.state = 'cancel'
        self.assertEqual(self.partner_id.loyalty_points, 100)

        self.env.user.partner_id = self.partner_id
        gift_card = self.reward_id._redeem_gift_card(self.env['website'].get_current_website())
        self.assertEqual(self.partner_id.loyalty_points, 25)
        self.assertEqual(gift_card.balance, 50)
        with self.assertRaises(UserError, msg="Insufficient points"):
            self.reward_id._redeem_gift_card(self.env['website'].get_current_website())
