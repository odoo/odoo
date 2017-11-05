# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class Test_Lunch(common.TransactionCase):

    def setUp(self):
        """*****setUp*****"""
        super(Test_Lunch, self).setUp()

        self.demo_user = self.env['res.users'].search([('name', '=', 'Demo User')])
        self.product_bolognese_ref = self.env['ir.model.data'].get_object_reference('lunch', 'product_Bolognese')
        self.product_Bolognese_id = self.product_bolognese_ref and self.product_bolognese_ref[1] or False
        self.new_id_order = self.env['lunch.order'].create({
            'user_id': self.demo_user.id,
            'order_line_ids': '[]',
            })
        self.new_id_order_line = self.env['lunch.order.line'].create({
            'order_id': self.new_id_order.id,
            'product_id': self.product_Bolognese_id,
            'note': '+Emmental',
            'cashmove': [],
            'price': self.env['lunch.product'].browse(self.product_Bolognese_id).price,
            })

    def test_00_lunch_order(self):
        """Change the state of an order line from 'new' to 'ordered'. Check that there are no cashmove linked to that order line"""
        self.order_one = self.new_id_order_line
        #we check that our order_line is a 'new' one and that there are no cashmove linked to that order_line:
        self.assertEqual(self.order_one.state, 'new')
        self.assertEqual(list(self.order_one.cashmove), [])
        #we order that orderline so it's state will be 'ordered'
        self.order_one.order()
        self.order_one = self.new_id_order_line
        #we check that our order_line is a 'ordered' one and that there are no cashmove linked to that order_line:
        self.assertEqual(self.order_one.state, 'ordered')
        self.assertEqual(list(self.order_one.cashmove), [])

    def test_01_lunch_order(self):
        """Change the state of an order line from 'new' to 'ordered' then to 'confirmed'. Check that there is a cashmove linked to the order line"""
        self.test_00_lunch_order()
        #We receive the order so we confirm the order line so it's state will be 'confirmed'
        #A cashmove will be created and we will test that the cashmove amount equals the order line price
        self.order_one.confirm()
        self.order_one = self.new_id_order_line
        #we check that our order_line is a 'confirmed' one and that there are a cashmove linked to that order_line with an amount equals to the order line price:
        self.assertEqual(self.order_one.state, 'confirmed')
        self.assertTrue(self.order_one.cashmove)
        self.assertTrue(self.order_one.cashmove[0].amount == -self.order_one.price)

    def test_02_lunch_order(self):
        """Change the state of an order line from 'confirmed' to 'cancelled' and check that the cashmove linked to that order line will be deleted"""
        self.test_01_lunch_order()
        #We have a confirmed order with its associate cashmove
        #We execute the cancel function
        self.order_one.cancel()
        self.order_one = self.new_id_order_line
        #We check that the state is cancelled and that the cashmove has been deleted
        self.assertEqual(self.order_one.state, 'cancelled')
        self.assertFalse(self.order_one.cashmove)
