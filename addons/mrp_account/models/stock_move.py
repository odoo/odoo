# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _filter_anglo_saxon_moves(self, product):
        res = super(StockMove, self)._filter_anglo_saxon_moves(product)
        res += self.filtered(lambda m: m.bom_line_id.bom_id.product_tmpl_id.id == product.product_tmpl_id.id)
        return res

    def _generate_analytic_lines_data(self, unit_amount, amount, distribution, account, distribution_on_each_plan):
        vals = super()._generate_analytic_lines_data(unit_amount, amount, distribution, account, distribution_on_each_plan)
        if self._get_analytic_distribution():
            vals['name'] = _('[Raw] %s', self.product_id.display_name)
            vals['ref'] = self.raw_material_production_id.display_name
            vals['category'] = 'manufacturing_order'
        return vals

    def _get_analytic_distribution(self):
        distribution = self.raw_material_production_id.analytic_distribution
        if distribution:
            return distribution
        return super()._get_analytic_distribution()

    def _ignore_automatic_valuation(self):
        return bool(self.raw_material_production_id)

    def _get_src_account(self, accounts_data):
        if self._is_production():
            return self.location_id.valuation_out_account_id.id or accounts_data['production'].id
        return super()._get_src_account(accounts_data)

    def _get_dest_account(self, accounts_data):
        if self._is_production_consumed():
            return self.location_dest_id.valuation_in_account_id.id or accounts_data['production'].id
        return super()._get_dest_account(accounts_data)

    def _is_production(self):
        self.ensure_one()
        return self.location_id.usage == 'production' and self.location_dest_id._should_be_valued()

    def _is_production_consumed(self):
        self.ensure_one()
        return self.location_dest_id.usage == 'production' and self.location_id._should_be_valued()
