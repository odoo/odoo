# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields
from openerp.osv import osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class mrp_subproduct(osv.osv):
    _name = 'mrp.subproduct'
    _description = 'Byproduct'
    _columns={
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_qty': fields.float('Product Qty', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'subproduct_type': fields.selection([('fixed','Fixed'),('variable','Variable')], 'Quantity Type', required=True, help="Define how the quantity of byproducts will be set on the production orders using this BoM.\
  'Fixed' depicts a situation where the quantity of created byproduct is always equal to the quantity set on the BoM, regardless of how many are created in the production order.\
  By opposition, 'Variable' means that the quantity will be computed as\
    '(quantity of byproduct set on the BoM / quantity of manufactured product set on the BoM * quantity of manufactured product in the production order.)'"),
        'bom_id': fields.many2one('mrp.bom', 'BoM', ondelete='cascade'),
    }
    _defaults={
        'subproduct_type': 'variable',
        'product_qty': lambda *a: 1.0,
    }

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        """ Changes UoM if product_id changes.
        @param product_id: Changed product_id
        @return: Dictionary of changed values
        """
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            v = {'product_uom': prod.uom_id.id}
            return {'value': v}
        return {}

    def onchange_uom(self, cr, uid, ids, product_id, product_uom, context=None):
        res = {'value':{}}
        if not product_uom or not product_id:
            return res
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        uom = self.pool.get('product.uom').browse(cr, uid, product_uom, context=context)
        if uom.category_id.id != product.uom_id.category_id.id:
            res['warning'] = {'title': _('Warning'), 'message': _('The Product Unit of Measure you chose has a different category than in the product form.')}
            res['value'].update({'product_uom': product.uom_id.id})
        return res
