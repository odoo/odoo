# -*- coding: utf-8 -*-

from openerp.osv import fields, osv

class product_pricelist(osv.osv):
    _inherit = 'product.pricelist'

    _columns = {
        'discount_policy': fields.selection([('with_discount', 'Discount included in the price'), ('without_discount', 'Show discount in the sale order')], string="Discount Policy"),
    }
    _defaults = {'discount_policy': 'with_discount'}