# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockBarcodeCancelPicking(models.TransientModel):
    _name = 'stock_barcode.cancel.operation'
    _description = 'Cancel Operation'

    picking_id = fields.Many2one('stock.picking', 'Transfer', readonly=True)
    picking_name = fields.Char('Transfer Name', readonly=True, related='picking_id.display_name')

    def action_cancel_operation(self):
        res = self.picking_id.action_cancel()
        return {'type': 'ir.actions.act_window_close', 'infos': {'cancelled': res}}
