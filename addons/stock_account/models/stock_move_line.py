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
            diff = move_line.qty_done
            if float_is_zero(diff, precision_rounding=move_line.move_id.product_id.uom_id.rounding):
                continue
            move_line._create_correction_svl(diff)
        return move_lines

    def write(self, vals):
        if 'qty_done' in vals:
            for move_line in self:
                if move_line.state != 'done':
                    continue
                diff = vals['qty_done'] - move_line.qty_done
                if float_is_zero(diff, precision_rounding=move_line.move_id.product_id.uom_id.rounding):
                    continue
                move_line._create_correction_svl(diff)
        return super(StockMoveLine, self).write(vals)

    # -------------------------------------------------------------------------
    # SVL creation helpers
    # -------------------------------------------------------------------------
    def _prepare_common_svl_vals(self):
        """When a `stock.valuation.layer` is created from a `stock.move.line`, we can prepare a dict of
        common vals.

        :returns: the common values when creating a `stock.valuation.layer` from a `stock.move.line`
        :rtype: dict
        """
        self.ensure_one()
        return {
            'stock_move_line_id': self.id,
            'stock_move_id': self.move_id.id,
            'company_id': self.move_id.company_id.id,
            'product_id': self.product_id.id,
            'description': self.move_id.name,
            'lot_id': self.lot_id and self.lot_id.id or False
        }

    def _create_in_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the qty_done of the move line (Default value = None)
        """
        svl_vals_list = []
        for line in self:
            # we don't want to create svl for a line that is not an in move line this case, unless we are asked to do with context
            if not self._context.get('force_create_svl', False) and line not in line.move_id._get_in_move_lines():
                continue

            valued_quantity = line.product_uom_id._compute_quantity(line.qty_done, line.product_id.uom_id)
            unit_cost = abs(line.move_id._get_price_unit())  # May be negative (i.e. decrease an out move.move_id).
            if line.product_id.cost_method == 'standard':
                unit_cost = line.product_id.standard_price
            svl_vals = line.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
            svl_vals.update(line._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % line.picking_id.name or line.move_id.name
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _create_out_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the qty_done of the move line (Default value = None)
        """
        svl_vals_list = []
        for line in self:
            # we don't want to create svl for a line that is not an out move line this case, unless we are asked to do with context
            if not self._context.get('force_create_svl', False) and line not in line.move_id._get_out_move_lines():
                continue

            valued_quantity = line.product_uom_id._compute_quantity(line.qty_done, line.product_id.uom_id)
            svl_vals = line.product_id._prepare_out_svl_vals(forced_quantity or valued_quantity, line.move_id.company_id, line.lot_id)
            svl_vals.update(line._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % line.picking_id.name or line.move_id.name
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _create_dropshipped_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the qty_done of the move line (Default value = None)
        """
        svl_vals_list = []
        for line in self:
            valued_quantity = line.product_uom_id._compute_quantity(line.qty_done, line.product_id.uom_id)
            quantity = forced_quantity or valued_quantity

            unit_cost = line.move_id._get_price_unit()
            if line.product_id.cost_method == 'standard':
                unit_cost = line.product_id.standard_price

            common_vals = dict(line._prepare_common_svl_vals(), remaining_qty=0)

            # create the in
            in_vals = {
                'unit_cost': unit_cost,
                'value': unit_cost * quantity,
                'quantity': quantity,
            }
            in_vals.update(common_vals)
            svl_vals_list.append(in_vals)

            # create the out
            out_vals = {
                'unit_cost': unit_cost,
                'value': unit_cost * quantity * -1,
                'quantity': quantity * -1,
            }
            out_vals.update(common_vals)
            svl_vals_list.append(out_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _create_dropshipped_returned_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the qty_done of the move line (Default value = None)
        """
        return self._create_dropshipped_svl(forced_quantity=forced_quantity)

    def _create_correction_svl(self, diff):
        self.ensure_one()
        move = self.move_id
        stock_valuation_layers = self.env['stock.valuation.layer']
        if move._is_in() and diff > 0 or move._is_out() and diff < 0:
            if move._is_out():
                self = self.with_context(force_create_svl=True)
            move.product_price_update_before_done(forced_qty=diff)
            stock_valuation_layers |= self._create_in_svl(forced_quantity=abs(diff))
        elif move._is_in() and diff < 0 or move._is_out() and diff > 0:
            if move._is_in():
                self = self.with_context(force_create_svl=True)
            stock_valuation_layers |= self._create_out_svl(forced_quantity=abs(diff))
        elif move._is_dropshipped() and diff > 0 or move._is_dropshipped_returned() and diff < 0:
            stock_valuation_layers |= self._create_dropshipped_svl(forced_quantity=abs(diff))
        elif move._is_dropshipped() and diff < 0 or move._is_dropshipped_returned() and diff > 0:
            stock_valuation_layers |= self._create_dropshipped_returned_svl(forced_quantity=abs(diff))

        for svl in stock_valuation_layers:
            if not svl.product_id.valuation == 'real_time':
                continue
            svl.stock_move_id._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)
