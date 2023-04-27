# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockTrackConfirmation(models.TransientModel):
    _name = 'stock.track.confirmation'
    _description = 'Stock Track Confirmation'

    tracking_line_ids = fields.One2many('stock.track.line', 'wizard_id')
    inventory_id = fields.Many2one('stock.inventory', 'Inventory')

    def action_confirm(self):
        for confirmation in self:
            confirmation.inventory_id._action_done()

class StockTrackingLines(models.TransientModel):
    _name = 'stock.track.line'
    _description = 'Stock Track Line'

    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    tracking = fields.Selection([('lot', 'Tracked by lot'), ('serial', 'Tracked by serial number')], readonly=True)
    wizard_id = fields.Many2one('stock.track.confirmation', readonly=True)
