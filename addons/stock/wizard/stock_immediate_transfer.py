# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class StockImmediateTransfer(models.TransientModel):
    _name = 'stock.immediate.transfer'
    _description = 'Immediate Transfer'

    pick_ids = fields.Many2many('stock.picking', 'stock_picking_transfer_rel')

    def process(self):
        pickings_to_process = self.pick_ids._check_no_quantities_done()
        for picking in pickings_to_process:
            # If still in draft => confirm and assign
            if picking.state == 'draft':
                picking.action_confirm()
                if picking.state != 'assigned':
                    picking.action_assign()
                    if picking.state != 'assigned':
                        raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
            for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty
        # Process every picking that do not require a backorder, then return a single backorder wizard for every other ones.
        return self.pick_ids.with_context(skip_no_quantity_check=True)._finalize_validation()
