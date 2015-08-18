# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
