# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import tools
from openerp.tests import common

class Test_Lunch(common.TransactionCase):

    def setUp(self):
        """*****setUp*****"""
        super(Test_Lunch, self).setUp()
        cr, uid = self.cr, self.uid

        self.res_users = self.registry('res.users')
        self.lunch_order = self.registry('lunch.order')
        self.lunch_order_line = self.registry('lunch.order.line')
        self.lunch_cashmove = self.registry('lunch.cashmove')
        self.lunch_product = self.registry('lunch.product')
        self.lunch_alert = self.registry('lunch.alert')
        self.lunch_product_category = self.registry('lunch.product.category')

        self.demo_id = self.res_users.search(cr, uid, [('name', '=', 'Demo User')])
        self.product_bolognese_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'lunch', 'product_Bolognese')
        self.product_Bolognese_id = self.product_bolognese_ref and self.product_bolognese_ref[1] or False
        self.new_id_order = self.lunch_order.create(cr,uid,{
            'user_id': self.demo_id[0],
            'order_line_ids':'[]',
            },context=None)
        self.new_id_order_line = self.lunch_order_line.create(cr,uid,{
            'order_id':self.new_id_order,
            'product_id':self.product_Bolognese_id,
            'note': '+Emmental',
            'cashmove': [],
            'price': self.lunch_product.browse(cr,uid,self.product_Bolognese_id,context=None).price,
            })

    def test_00_lunch_order(self):
        """Change the state of an order line from 'new' to 'ordered'. Check that there are no cashmove linked to that order line"""
        cr, uid = self.cr, self.uid
        self.order_one = self.lunch_order_line.browse(cr,uid,self.new_id_order_line,context=None)
        #we check that our order_line is a 'new' one and that there are no cashmove linked to that order_line:
        self.assertEqual(self.order_one.state,'new')
        self.assertEqual(list(self.order_one.cashmove), [])
        #we order that orderline so it's state will be 'ordered'
        self.order_one.order()
        self.order_one = self.lunch_order_line.browse(cr,uid,self.new_id_order_line,context=None)
        #we check that our order_line is a 'ordered' one and that there are no cashmove linked to that order_line:
        self.assertEqual(self.order_one.state,'ordered')
        self.assertEqual(list(self.order_one.cashmove), [])

    def test_01_lunch_order(self):
        """Change the state of an order line from 'new' to 'ordered' then to 'confirmed'. Check that there is a cashmove linked to the order line"""
        cr, uid = self.cr, self.uid
        self.test_00_lunch_order()
        #We receive the order so we confirm the order line so it's state will be 'confirmed'
        #A cashmove will be created and we will test that the cashmove amount equals the order line price
        self.order_one.confirm()
        self.order_one = self.lunch_order_line.browse(cr,uid,self.new_id_order_line,context=None)
        #we check that our order_line is a 'confirmed' one and that there are a cashmove linked to that order_line with an amount equals to the order line price:
        self.assertEqual(self.order_one.state,'confirmed')
        self.assertTrue(self.order_one.cashmove)
        self.assertTrue(self.order_one.cashmove[0].amount==-self.order_one.price)

    def test_02_lunch_order(self):
        """Change the state of an order line from 'confirmed' to 'cancelled' and check that the cashmove linked to that order line will be deleted"""
        cr, uid = self.cr, self.uid
        self.test_01_lunch_order()
        #We have a confirmed order with its associate cashmove
        #We execute the cancel function
        self.order_one.cancel()
        self.order_one = self.lunch_order_line.browse(cr,uid,self.new_id_order_line,context=None)
        #We check that the state is cancelled and that the cashmove has been deleted
        self.assertEqual(self.order_one.state,'cancelled')
        self.assertFalse(self.order_one.cashmove)