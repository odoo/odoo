# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class MrpSubProduct(models.Model):
    _name = 'mrp.subproduct'
    _description = 'Byproduct'

    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_qty = fields.Float(
        'Product Qty',
        default=1.0, digits_compute=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom = fields.Many2one('product.uom', 'Product Unit of Measure', required=True)
    subproduct_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('variable', 'Variable')], string='Quantity Type',
        default='variable', required=True,
        help="Define how the quantity of byproducts will be set on the production orders using this BoM.\n"
             "'Fixed' depicts a situation where the quantity of created byproduct is always equal to the "
             " quantity set on the BoM, regardless of how many are created in the production order.\n"
             "By opposition, 'Variable' means that the quantity will be computed as (quantity of byproduct "
             "set on the BoM / quantity of manufactured product set on the BoM * quantity of manufactured "
             "product in the production order.)")
    bom_id = fields.Many2one('mrp.bom', 'BoM', ondelete='cascade')

    @api.onchange('product_id')
    def onchange_product_id(self):
        """ Changes UoM if product_id changes. """
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id

    @api.onchange('product_uom')
    def onchange_uom(self):
        res = {}
        if self.product_uom and self.product_id and self.product_uom.category_id != self.product_id.uom_id.category_id:
            res['warning'] = {
                'title': _('Warning'),
                'message': _('The Product Unit of Measure you chose has a different category than in the product form.')
            }
            self.product_uom = self.product_id.uom_id.id
        return res
