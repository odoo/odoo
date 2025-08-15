# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, Command, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _filter_anglo_saxon_moves(self, product):
        res = super(StockMove, self)._filter_anglo_saxon_moves(product)
        res += self.filtered(lambda m: m.bom_line_id.bom_id.product_tmpl_id.id == product.product_tmpl_id.id)
        return res

    def _get_analytic_distribution(self):
        distribution = self.raw_material_production_id.analytic_distribution
        if distribution:
            return distribution
        return super()._get_analytic_distribution()

    def _should_force_price_unit(self):
        self.ensure_one()
        return ((self.picking_type_id.code == 'mrp_operation' and self.production_id) or
                super()._should_force_price_unit()
        )

    def _ignore_automatic_valuation(self):
        return bool(self.raw_material_production_id)

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

    def _create_out_svl(self, forced_quantity=None):
        svls = super()._create_out_svl(forced_quantity)
        unbuild_svls = svls.filtered('stock_move_id.unbuild_id')
        unbuild_cost_correction_move_list = list()
        for svl in unbuild_svls:
            build_time_unit_cost = svl.stock_move_id.unbuild_id.mo_id.move_finished_ids.filtered(
                lambda m: m.product_id == svl.product_id
            ).stock_valuation_layer_ids.unit_cost
            unbuild_difference = svl.unit_cost - build_time_unit_cost
            if svl.product_id.valuation == 'real_time' and not svl.currency_id.is_zero(unbuild_difference):
                product_accounts = svl.product_id.product_tmpl_id.get_product_accounts()
                valuation_account, production_account = (
                    product_accounts['stock_valuation'],
                    product_accounts['production'],
                )
                desc = _('%s - Unbuild Cost Difference', svl.stock_move_id.unbuild_id.name)
                unbuild_cost_correction_move_list.append({
                    'journal_id': product_accounts['stock_journal'].id,
                    'date': fields.Date.context_today(self),
                    'ref': desc,
                    'move_type': 'entry',
                    'line_ids': [Command.create({
                        'name': desc,
                        'ref': desc,
                        'account_id': account.id,
                        'balance': balance,
                        'product_id': svl.product_id.id,
                    }) for account, balance in (
                        (valuation_account, unbuild_difference),
                        (production_account, -unbuild_difference),
                    )],
                })
        if unbuild_cost_correction_move_list:
            unbuild_cost_correction_moves = self.env['account.move'].sudo().create(unbuild_cost_correction_move_list)
            unbuild_cost_correction_moves._post()
        return svls

    def _get_all_related_sm(self, product):
        moves = super()._get_all_related_sm(product)
        return moves | self.filtered(
            lambda m:
            m.bom_line_id.bom_id.type == 'phantom' and
            m.bom_line_id.bom_id == moves.bom_line_id.bom_id
        )
