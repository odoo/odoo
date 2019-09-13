# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare


class StockBackorderConfirmation(models.TransientModel):
    _name = 'stock.backorder.confirmation'
    _description = 'Backorder Confirmation'

    pick_ids = fields.Many2many('stock.picking', 'stock_picking_backorder_rel')

    def _process(self, cancel_backorder=False):
        for confirmation in self:
            if cancel_backorder:
                for pick_id in confirmation.pick_ids:
                    moves_to_log = {}
                    for move in pick_id.move_lines:
                        if float_compare(move.product_uom_qty,
                                         move.quantity_done,
                                         precision_rounding=move.product_uom.rounding) > 0:
                            moves_to_log[move] = (move.quantity_done, move.product_uom_qty)
                    pick_id._log_less_quantities_than_expected(moves_to_log)
            confirmation.pick_ids.with_context(cancel_backorder=cancel_backorder).action_done()

    def process(self):
        self._process()

    def process_cancel_backorder(self):
        self._process(cancel_backorder=True)
