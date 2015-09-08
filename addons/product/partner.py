# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'
    _columns = {
        'property_product_pricelist': fields.property(
            type='many2one', 
            relation='product.pricelist', 
            string="Sale Pricelist", 
            help="This pricelist will be used, instead of the default one, for sales to the current partner"),
    }

    def _commercial_fields(self, cr, uid, context=None):
        return super(res_partner, self)._commercial_fields(cr, uid, context=context) + ['property_product_pricelist']
