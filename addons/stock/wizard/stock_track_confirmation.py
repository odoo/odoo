# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockTrackConfirmation(models.TransientModel):
    _name = 'stock.track.confirmation'
    _description = 'Stock Track Confirmation'

    tracking_line_ids = fields.One2many('stock.track.line', 'wizard_id')
    quant_ids = fields.Many2many('stock.quant', string='Quants')
    product_ids = fields.Many2many('product.product', string='Products')

    def action_confirm(self):
        self.quant_ids._apply_inventory()
        self.quant_ids.inventory_quantity_set = False

    @api.onchange('product_ids')
    def _onchange_quants(self):
        self.tracking_line_ids = [(0, 0, {'product_id': product}) for product in self.product_ids]


class StockTrackingLines(models.TransientModel):
    _name = 'stock.track.line'
    _description = 'Stock Track Line'

    product_display_name = fields.Char('Name', compute='_compute_product_display_name', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    tracking = fields.Selection(related='product_id.tracking')
    wizard_id = fields.Many2one('stock.track.confirmation', readonly=True)

    def _compute_product_display_name(self):
        """ Onchange results in product.display_name not being directly accessible """
        for line in self:
            line.product_display_name = line.product_id._origin.display_name
