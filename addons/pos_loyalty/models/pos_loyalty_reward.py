# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)


class loyalty_reward(osv.osv):
    _name = 'loyalty.reward'
    _columns = {
        'name':                 fields.char('Name', size=32, select=1, required=True, help='An internal identification for this loyalty reward'),
        'loyalty_program_id':   fields.many2one('loyalty.program', 'Loyalty Program', help='The Loyalty Program this reward belongs to'),
        'minimum_points':       fields.float('Minimum Points', help='The minimum amount of points the customer must have to qualify for this reward'),
        'type':                 fields.selection((('gift','Gift'),('discount','Discount'),('resale','Resale')), 'Type', required=True, help='The type of the reward'),
        'gift_product_id':           fields.many2one('product.product','Gift Product', help='The product given as a reward'),
        'point_cost':           fields.float('Point Cost', help='The cost of the reward'),
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
