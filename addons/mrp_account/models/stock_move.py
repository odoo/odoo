# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.tools import float_is_zero


class StockMove(models.Model):
    _inherit = "stock.move"

    def _filter_anglo_saxon_moves(self, product):
        res = super(StockMove, self)._filter_anglo_saxon_moves(product)
        res += self.filtered(lambda m: m.bom_line_id.bom_id.product_tmpl_id.id == product.product_tmpl_id.id)
        return res

    def _generate_analytic_lines_data(self, unit_amount, amount):
        vals = super()._generate_analytic_lines_data(unit_amount, amount)
        if self.raw_material_production_id.analytic_account_id:
            vals['name'] = _('[Raw] %s', self.product_id.display_name)
            vals['ref'] = self.raw_material_production_id.display_name
            vals['category'] = 'manufacturing_order'
        return vals

    def _get_analytic_account(self):
        account = self.raw_material_production_id.analytic_account_id
        if account:
            return account
        return super()._get_analytic_account()

    def _get_src_account(self, accounts_data):
        if not self.unbuild_id:
            return super()._get_src_account(accounts_data)
        else:
            return self.location_dest_id.valuation_out_account_id.id or accounts_data['stock_input'].id

    def _get_dest_account(self, accounts_data):
        if not self.unbuild_id:
            return super()._get_dest_account(accounts_data)
        else:
            return self.location_id.valuation_in_account_id.id or accounts_data['stock_output'].id

    def _is_returned(self, valued_type):
        if self.unbuild_id:
            return True
        return super()._is_returned(valued_type)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.model_create_multi
    def create(self, vals_list):
        move_lines = super(StockMoveLine, self).create(vals_list)
        for move_line in move_lines:
            move = move_line.move_id
            production = move.production_id or move.raw_material_production_id
            float_qty_check = float_is_zero(move_line.qty_done, precision_digits=move_line.product_uom_id.rounding)
            if production and not float_qty_check and not self._context.get('button_mark_done_production_ids'):
                self._correction_svl_after_production(production, move)
        return move_lines

    def write(self, vals):
        res = super(StockMoveLine, self).write(vals)
        if 'qty_done' in vals:
            for move_line in self:
                move = move_line.move_id
                production = move.production_id or move.raw_material_production_id
                if production:
                    self._correction_svl_after_production(production, move)
        return res

    @api.model
    def _correction_svl_after_production(self, production, move):
        """ For flexible consumption in AVCO and FIFO product category, Create valuation layer from
            1. Creating new line in Manufacturing order's components or byproducts
            2. Change quantity in existing Manufacturing order's components, byproducts or production """
        if production.state == 'done' and production.product_id.cost_method in ('average', 'fifo'):
            current_svl = move.stock_valuation_layer_ids.filtered(lambda l: l.quantity).sorted(
                lambda l: l.create_date and l.id, reverse=True)
            if current_svl:
                production_diff = current_svl[0].value * -1
                # Add new By-product or Change qty in Finished Product or By-proudct Manufacturing
                if move.production_id:
                    self._create_correction_svl_done_mo(production, move, production_diff)
                # Add new line in Components of Manufacturing or Change qty in Components of Manufacturing
                elif move.raw_material_production_id:
                    production_diff, byproducts_diff = self._split_production_and_by_product_cost(production_diff,
                                                                                                  production)
                    # Create diff stock valuation for by product
                    for byproduct_move, byproduct_diff in byproducts_diff.items():
                        self._create_correction_svl_done_mo(production, byproduct_move, byproduct_diff)
                    # Create diff stock valuation for finished product
                    production_move = production.move_finished_ids.filtered(
                        lambda l: l.product_id == production.product_id)
                    self._create_correction_svl_done_mo(production, production_move, production_diff)

    @api.model
    def _split_production_and_by_product_cost(self, production_cost, production):
        """ Return production cost diff and dictionary of byproduct move and byproduct cost
            for create valuation layer in done manufacturing order """
        byproduct_cost = {}
        for move in production.move_byproduct_ids:
            if move.cost_share:
                cost = (production_cost * move.cost_share) / 100
                byproduct_cost.update({move: cost})
        return production_cost - sum(byproduct_cost.values()), byproduct_cost

    @api.model
    def _create_correction_svl_done_mo(self, production, move, cost):
        """ Create valuation layer for done manufacturing order and production's product category is Done or Fifo """
        StockValuationLayer = self.env['stock.valuation.layer']
        svl_vals = move._prepare_common_svl_vals()
        svl_vals.update({
            'product_id': move.product_id.id,
            'value': cost,
            'unit_cost': cost,
            'quantity': 0,
            'description': 'Correction of Manufacturing Order %s' % production.name or move.name
        })
        svl_vals_list = [svl_vals]
        svl = StockValuationLayer.sudo().create(svl_vals_list)
        svl._validate_accounting_entries()
