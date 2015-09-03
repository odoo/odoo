# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import logging

import openerp

from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class loyalty_program(osv.osv):
    _name = 'loyalty.program'
    _columns = {
        'name' :        fields.char('Loyalty Program Name', size=32, select=1,
             required=True, help="An internal identification for the loyalty program configuration"),
        'pp_currency':  fields.float('Points per currency',help="How many loyalty points are given to the customer by sold currency"),
        'pp_product':   fields.float('Points per product',help="How many loyalty points are given to the customer by product sold"),
        'pp_order':     fields.float('Points per order',help="How many loyalty points are given to the customer for each sale or order"),
        'rounding':     fields.float('Points Rounding', help="The loyalty point amounts are rounded to multiples of this value."),
        'rule_ids':     fields.one2many('loyalty.rule','loyalty_program_id','Rules'),
        'reward_ids':   fields.one2many('loyalty.reward','loyalty_program_id','Rewards'),
        
    }
    _defaults = {
        'rounding': 1,
    }

class loyalty_rule(osv.osv):
    _name = 'loyalty.rule'
    _columns = {
        'name':                 fields.char('Name', size=32, select=1, required=True, help="An internal identification for this loyalty program rule"),
        'loyalty_program_id':   fields.many2one('loyalty.program', 'Loyalty Program', help='The Loyalty Program this exception belongs to'),
        'type':                 fields.selection((('product','Product'),('category','Category')), 'Type', required=True, help='Does this rule affects products, or a category of products ?'),
        'product_id':           fields.many2one('product.product','Target Product',  help='The product affected by the rule'),
        'category_id':          fields.many2one('pos.category',   'Target Category', help='The category affected by the rule'),
        'cumulative':           fields.boolean('Cumulative',        help='The points won from this rule will be won in addition to other rules'),
        'pp_product':           fields.float('Points per product',  help='How many points the product will earn per product ordered'),
        'pp_currency':          fields.float('Points per currency', help='How many points the product will earn per value sold'),
    }
    _defaults = {
        'type':'product',
    }


class loyalty_reward(osv.osv):
    _name = 'loyalty.reward'
    _columns = {
        'name':                 fields.char('Name', size=32, select=1, required=True, help='An internal identification for this loyalty reward'),
        'loyalty_program_id':   fields.many2one('loyalty.program', 'Loyalty Program', help='The Loyalty Program this reward belongs to'),
        'minimum_points':       fields.float('Minimum Points', help='The minimum amount of points the customer must have to qualify for this reward'),
        'type':                 fields.selection((('gift','Gift'),('discount','Discount'),('resale','Resale')), 'Type', required=True, help='The type of the reward'),
        'gift_product_id':           fields.many2one('product.product','Gift Product', help='The product given as a reward'),
        'point_cost':           fields.float('Point Cost', help='The cost of the reward per moneytary unit discounted'),
        'discount_product_id':  fields.many2one('product.product','Discount Product', help='The product used to apply discounts'),
        'discount':             fields.float('Discount',help='The discount percentage'),
        'point_product_id':    fields.many2one('product.product', 'Point Product', help='The product that represents a point that is sold by the customer'),
    }

    def _check_gift_product(self, cr, uid, ids, context=None):
        for reward in self.browse(cr, uid, ids, context=context):
            if reward.type == 'gift':
                return bool(reward.gift_product_id)
            else:
                return True

    def _check_discount_product(self, cr, uid, ids, context=None):
        for reward in self.browse(cr, uid, ids, context=context):
            if reward.type == 'discount':
                return bool(reward.discount_product_id)
            else:
                return True

    def _check_point_product(self, cr, uid, ids, context=None):
        for reward in self.browse(cr, uid, ids, context=context):
            if reward.type == 'resale':
                return bool(reward.point_product_id)
            else:
                return True

    _constraints = [
        (_check_gift_product,     "The gift product field is mandatory for gift rewards",         ["type","gift_product_id"]),
        (_check_discount_product, "The discount product field is mandatory for discount rewards", ["type","discount_product_id"]),
        (_check_point_product,    "The point product field is mandatory for point resale rewards", ["type","discount_product_id"]),
    ]

class pos_config(osv.osv):
    _inherit = 'pos.config' 
    _columns = {
        'loyalty_id': fields.many2one('loyalty.program','Loyalty Program', help='The loyalty program used by this point_of_sale'),
        
    }

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'loyalty_points': fields.float('Loyalty Points', help='The loyalty points the user won as part of a Loyalty Program')
    }

class pos_order(osv.osv):
    _inherit = 'pos.order'

    _columns = {
        'loyalty_points': fields.float('Loyalty Points', help='The amount of Loyalty points the customer won or lost with this order'),
    }

    def _order_fields(self, cr, uid, ui_order, context=None):
        fields = super(pos_order,self)._order_fields(cr,uid,ui_order,context)
        fields['loyalty_points'] = ui_order.get('loyalty_points',0)
        return fields

    def create_from_ui(self, cr, uid, orders, context=None):
        ids = super(pos_order,self).create_from_ui(cr,uid,orders,context=context)
        for order in orders:
            if order['data']['loyalty_points'] != 0 and order['data']['partner_id']:
                partner = self.pool.get('res.partner').browse(cr,uid,order['data']['partner_id'], context=context)
                partner.write({'loyalty_points': partner['loyalty_points'] + order['data']['loyalty_points']})

        return ids
            
             
    
