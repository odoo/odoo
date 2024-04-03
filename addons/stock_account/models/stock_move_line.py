# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_compare, float_is_zero


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        analytic_move_to_recompute = set()
        move_lines = super(StockMoveLine, self).create(vals_list)
        for move_line in move_lines:
            move = move_line.move_id
            analytic_move_to_recompute.add(move.id)
            if move_line.state != 'done':
                continue
            rounding = move.product_id.uom_id.rounding
            diff = move.product_uom._compute_quantity(move_line.qty_done, move.product_id.uom_id)
            if float_is_zero(diff, precision_rounding=rounding):
                continue
            self._create_correction_svl(move, diff)
        if analytic_move_to_recompute:
            self.env['stock.move'].browse(
                analytic_move_to_recompute)._account_analytic_entry_move()
        return move_lines

    def write(self, vals):
        analytic_move_to_recompute = set()
        if 'qty_done' in vals or 'move_id' in vals:
            for move_line in self:
                move_id = vals.get('move_id') if vals.get('move_id') else move_line.move_id.id
                analytic_move_to_recompute.add(move_id)
        if 'qty_done' in vals:
            for move_line in self:
                if move_line.state != 'done':
                    continue
                move = move_line.move_id
                if float_compare(vals['qty_done'], move_line.qty_done, precision_rounding=move.product_uom.rounding) == 0:
                    continue
                rounding = move.product_id.uom_id.rounding
                diff = move.product_uom._compute_quantity(vals['qty_done'] - move_line.qty_done, move.product_id.uom_id, rounding_method='HALF-UP')
                if float_is_zero(diff, precision_rounding=rounding):
                    continue
                self._create_correction_svl(move, diff)
        res = super(StockMoveLine, self).write(vals)
        if analytic_move_to_recompute:
            self.env['stock.move'].browse(analytic_move_to_recompute)._account_analytic_entry_move()
        return res

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

        stock_valuation_layers._validate_accounting_entries()

    @api.model
    def _should_exclude_for_valuation(self):
        """
        Determines if this move line should be excluded from valuation based on its ownership.
        :return: True if the move line's owner is different from the company's partner (indicating
                it should be excluded from valuation), False otherwise.
        """
        self.ensure_one()
        return self.owner_id and self.owner_id != self.company_id.partner_id
