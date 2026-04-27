# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockBarcodeCancelPicking(models.TransientModel):
    _inherit = 'stock_barcode.cancel.operation'

    batch_id = fields.Many2one('stock.picking.batch', 'Batch Transfer', readonly=True)
    batch_name = fields.Char('Batch Transfer Name', readonly=True, related='batch_id.name')

    def action_cancel_operation(self):
        if self.batch_id:
            res = self.batch_id.action_cancel()
            return {'type': 'ir.actions.act_window_close', 'infos': {'cancelled': res}}
        return super().action_cancel_operation()
