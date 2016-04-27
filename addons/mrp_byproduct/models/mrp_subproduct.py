# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp


class MrpSubproduct(models.Model):
    _name = 'mrp.subproduct'
    _description = 'Byproduct'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_qty = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)
    product_uom_id = fields.Many2one('product.uom', 'Unit of Measure', required=True, oldname='product_uom')
    bom_id = fields.Many2one('mrp.bom', string='BoM')
    operation_id = fields.Many2one('mrp.routing.workcenter', 'Produced at Operation')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id

    @api.onchange('product_uom_id')
    def onchange_uom(self):
        res = {}
        if self.product_uom_id.category_id != self.product_id.uom_id.category_id:
            self.product_uom_id = self.product_id.uom_id.id
            res['warning'] = {'title': _('Warning'), 'message': _('The Product Unit of Measure you chose has a different category than in the product form.')}
        return res
