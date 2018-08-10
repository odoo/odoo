# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import common

from datetime import date, datetime
from unittest.mock import patch

class Test_Lunch(common.TransactionCase):

    def setUp(self):
        """*****setUp*****"""
        super(Test_Lunch, self).setUp()

        self.demo_user = self.env['res.users'].search([('name', '=', 'Marc Brown')])
        self.product_Bolognese_id = self.env.ref('lunch.product_Bolognese')
        self.new_id_order = self.env['lunch.order'].create({
            'user_id': self.demo_user.id,
            'order_line_ids': '[]',
            })
        self.new_id_order_line = self.env['lunch.order.line'].create({
            'order_id': self.new_id_order.id,
            'product_id': self.product_Bolognese_id.id,
            'note': '+Emmental',
            'cashmove': [],
            'price': self.product_Bolognese_id.price,
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

    def test_03_lunch_alert(self):
        """ specify a lunch alert and make sure it is not possible to make an
        order that day
        """
        alert_01 = self.env['lunch.alert'].create({
            'message': 'Order Bolognese only on Tuesday',
            'partner_id': self.product_Bolognese_id.supplier.id,
            'alert_type': 'week',
            'tuesday': True
        })

        patcher_date = patch('odoo.addons.lunch.models.lunch.datetime.date', wraps=date)
        patcher_datetime = patch('odoo.addons.lunch.models.lunch.datetime.datetime', wraps=datetime)
        mock_date = patcher_date.start()
        mock_datetime = patcher_datetime.start()

        mock_date.today.return_value = date(2018, 8, 14)  # a Tuesday
        mock_datetime.now.return_value = datetime(2018, 8, 14, 9, 0, 0)

        # We check that we can make an order on a Tuesday
        order_01 = self.env['lunch.order'].create({
            'user_id': self.demo_user.id,
            'order_line_ids': [(0, 0, {
                'product_id': self.product_Bolognese_id.id,
            })]
        })
        order_01.order_line_ids.order()

        with self.assertRaises(ValidationError):
            # Planning an order to an non-authorized day must not be possible
            order_02 = self.env['lunch.order'].create({
                'user_id': self.demo_user.id,
                'date': "2018-08-15",
                'order_line_ids': [(0, 0, {
                    'product_id': self.product_Bolognese_id.id,
                })]
            })

        alert_02 = self.env['lunch.alert'].create({
            'message': 'Working one more day',
            'partner_id': self.product_Bolognese_id.supplier.id,
            'alert_type': 'specific',
            'specific_day': date(2018, 8, 15)
        })

        # should now be possible to order tomorrow
        order_03 = self.env['lunch.order'].create({
            'user_id': self.demo_user.id,
            'date': "2018-08-15",
            'order_line_ids': [(0, 0, {
                'product_id': self.product_Bolognese_id.id,
            })]
        })

        # should be possible to planned on an allowed day
        order_04 = self.env['lunch.order'].create({
            'user_id': self.demo_user.id,
            'date': "2018-08-21",  # next Tuesday
            'order_line_ids': [(0, 0, {
                'product_id': self.product_Bolognese_id.id,
            })]
        })
        order_04.order_line_ids.order()

        # combinaision of alerts should work
        alert_03 = self.env['lunch.alert'].create({
            'message': 'Order Bolognese also on Wednesday',
            'partner_id': self.product_Bolognese_id.supplier.id,
            'alert_type': 'week',
            'wednesday': True
        })
        # Planning an order Wednesday must now be possible
        order_05 = self.env['lunch.order'].create({
            'user_id': self.demo_user.id,
            'date': "2018-08-22",  # next Wednesday
            'order_line_ids': [(0, 0, {
                'product_id': self.product_Bolognese_id.id,
            })]
        })
        order_05.order_line_ids.order()


        patcher_date.stop()
        patcher_datetime.stop()
