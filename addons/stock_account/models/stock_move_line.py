# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_is_zero


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        move_lines = super(StockMoveLine, self).create(vals_list)
        for move_line in move_lines:
            if move_line.state != 'done':
                continue
            move = move_line.move_id
            rounding = move.product_id.uom_id.rounding
            diff = move_line.qty_done
            if float_is_zero(diff, precision_rounding=rounding):
                continue
            self._create_correction_svl(move, diff)
        return move_lines

    def write(self, vals):
        if 'qty_done' in vals:
            for move_line in self:
                if move_line.state != 'done':
                    continue
                move = move_line.move_id
                rounding = move.product_id.uom_id.rounding
                diff = vals['qty_done'] - move_line.qty_done
                if float_is_zero(diff, precision_rounding=rounding):
                    continue
                self._create_correction_svl(move, diff)
        return super(StockMoveLine, self).write(vals)

    # -------------------------------------------------------------------------
    # SVL creation helpers
    # -------------------------------------------------------------------------
    @api.model
    def _create_correction_svl(self, move, diff):
        stock_valuation_layers = self.env['stock.valuation.layer']
        if move._is_in() and diff > 0 or move._is_out() and diff < 0:
            move.product_price_update_before_done(forced_qty=diff)
            stock_valuation_layers |= move._create_in_svl(forced_quantity=abs(diff))
            if move.product_id.cost_method in ('average', 'fifo'):
                move.product_id._run_fifo_vacuum(move.company_id)
        elif move._is_in() and diff < 0 or move._is_out() and diff > 0:
            stock_valuation_layers |= move._create_out_svl(forced_quantity=abs(diff))
        elif move._is_dropshipped() and diff > 0 or move._is_dropshipped_returned() and diff < 0:
            stock_valuation_layers |= move._create_dropshipped_svl(forced_quantity=abs(diff))
        elif move._is_dropshipped() and diff < 0 or move._is_dropshipped_returned() and diff > 0:
            stock_valuation_layers |= move._create_dropshipped_returned_svl(forced_quantity=abs(diff))

        for svl in stock_valuation_layers:
            if not svl.product_id.valuation == 'real_time':
                continue
            svl.stock_move_id._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)
