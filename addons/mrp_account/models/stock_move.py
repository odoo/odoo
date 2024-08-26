# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import models
from odoo.tools import float_round


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

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        rslt = super()._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description)

        product_expense_account = self.product_id.product_tmpl_id.get_product_accounts()['expense']
        labour_amounts = defaultdict(float)
        for wo in self.production_id.workorder_ids:
            account = wo.workcenter_id.expense_account_id or product_expense_account
            labour_amounts[account] += wo._cal_cost()
        workcenter_cost = sum(labour_amounts.values())

        if self.company_id.currency_id.is_zero(workcenter_cost):
            return rslt

        cost_share = 1
        if self.production_id.move_byproduct_ids:
            if self.cost_share:
                cost_share = self.cost_share / 100
            else:
                cost_share = float_round(1 - sum(self.production_id.move_byproduct_ids.mapped('cost_share')) / 100, precision_rounding=0.0001)
        rslt['credit_line_vals']['balance'] += workcenter_cost * cost_share
        for acc, amt in labour_amounts.items():
            rslt['labour_credit_line_vals_' + acc.code] = {
                'name': description,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': partner_id,
                'balance': -amt * cost_share,
                'account_id': acc.id,
            }
        return rslt
