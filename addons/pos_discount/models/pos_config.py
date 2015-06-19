# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import openerp

from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

class pos_config(osv.osv):
    _inherit = 'pos.config' 
    _columns = {
        'iface_discount': fields.boolean('Order Discounts', help='Allow the cashier to give discounts on the whole order.'),
        'discount_pc': fields.float('Discount Percentage', help='The default discount percentage'),
        'discount_product_id': fields.many2one('product.product','Discount Product', help='The product used to model the discount'),
    }
    _defaults = {
        'iface_discount': True,
        'discount_pc': 10,
    }
