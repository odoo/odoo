# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
import openerp.addons.decimal_precision as dp


class ProductTemplate(models.Model):
    _inherit = "product.template"

    uos_id = fields.Many2one('product.uom', 'Unit of Sale',
                             help='Specify a unit of measure here if invoicing is made in another'
                             ' unit of measure than inventory. Keep empty to use the default unit of measure.')
    uos_coeff = fields.Float('Unit of Measure -> UOS Coeff', digits=dp.get_precision('Product Unit of Measure'),
                             help='Coefficient to convert default Unit of Measure to Unit of Sale'
                             ' uos = uom * coeff')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.one
    def _set_uos(self):
        if self.product_id.uos_coeff:
            self.product_uom_qty = self.product_uos_qty / self.product_id.uos_coeff
            self.product_uom = self.product_id.uom_id

    @api.one
    def _compute_uos(self):
        self.product_uos_qty = self.product_uom_qty * self.product_id.uos_coeff

    product_uos_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'),
                                   compute='_compute_uos', inverse='_set_uos', readonly=False)
    product_uos = fields.Many2one('product.uom', string='Unit of Measure', required=True,
                                  related='product_id.uos_id', readonly=True)
