# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _filter_anglo_saxon_moves(self, product):
        res = super(StockMove, self)._filter_anglo_saxon_moves(product)
        res += self.filtered(lambda m: m.bom_line_id.bom_id.product_tmpl_id.id == product.product_tmpl_id.id)
        return res

    def _should_force_price_unit(self):
        self.ensure_one()
        return ((self.picking_type_id.code == 'mrp_operation' and self.production_id) or
                super()._should_force_price_unit()
        )

    def _ignore_automatic_valuation(self):
        return super()._ignore_automatic_valuation() or bool(self.raw_material_production_id)

    def _get_src_account(self, accounts_data):
        if self._is_production():
            return self.location_id.valuation_out_account_id.id or accounts_data['production'].id or accounts_data['stock_input'].id
        return super()._get_src_account(accounts_data)

    def _get_dest_account(self, accounts_data):
        if self._is_production_consumed():
            return self.location_dest_id.valuation_in_account_id.id or accounts_data['production'].id or accounts_data['stock_output'].id
        return super()._get_dest_account(accounts_data)

    def _is_production(self):
        self.ensure_one()
        return self.location_id.usage == 'production' and self.location_dest_id._should_be_valued()

    def _is_production_consumed(self):
        self.ensure_one()
        return self.location_dest_id.usage == 'production' and self.location_id._should_be_valued()

    def _get_out_svl_vals(self, forced_quantity):
        unbuild_moves = self.filtered('unbuild_id')
        # 'real cost' of finished product moves @ build time
        price_unit_map = {
            move.id: (
                move.unbuild_id.mo_id.move_finished_ids.stock_valuation_layer_ids.filtered(
                    lambda svl: svl.product_id == move.product_id
                )[0].unit_cost,
                move.company_id.currency_id.round,
            )
            for move in unbuild_moves.sudo()
            if move.product_id.cost_method != 'standard' and
            move.unbuild_id.mo_id.move_finished_ids.stock_valuation_layer_ids
        }
        svl_vals_list = super()._get_out_svl_vals(forced_quantity)
        if price_unit_map:
            for svl_vals in svl_vals_list:
                if (move_id := svl_vals['stock_move_id']) in price_unit_map:
                    unit_cost = price_unit_map[move_id][0]
                    svl_vals.update({
                        'unit_cost': unit_cost,
                        'value': price_unit_map[move_id][1](unit_cost * svl_vals['quantity']),
                    })
        return svl_vals_list

    def _create_out_svl(self, forced_quantity=None):
        product_unbuild_map = defaultdict(self.env['mrp.unbuild'].browse)
        for move in self:
            if move.unbuild_id:
                product_unbuild_map[move.product_id] |= move.unbuild_id
        return super(StockMove, self.with_context(product_unbuild_map=product_unbuild_map))._create_out_svl(forced_quantity)
