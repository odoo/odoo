# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import float_round


class ReportMrpReport_Mo_Overview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _get_report_data(self, production_id):
        res = super()._get_report_data(production_id)
        production = self.env['mrp.production'].browse(production_id)
        self._update_summary_with_extra_cost_values(res['summary'], production, res['summary']['quantity'])
        res['extras']['unit_mo_cost'] += production.extra_cost * self._get_remaining_cost_share(production)
        return res

    def _get_remaining_cost_share(self, production):
        byproducts_cost_share = sum(
            move.cost_share
            for move in production.move_byproduct_ids
            if (move.product_uom_qty if production.state != 'done' else move.quantity) > 0
        )
        return float_round(1 - byproducts_cost_share / 100, precision_rounding=0.0001)

    def _get_byproducts_data(self, production, current_mo_cost, level=0, current_index=False):
        current_mo_cost += production.extra_cost * (production.product_qty if production.state != 'done' else production.qty_produced)
        return super()._get_byproducts_data(production, current_mo_cost, level, current_index)

    def _get_report_extra_lines(self, summary, components, operations, production):
        res = super()._get_report_extra_lines(summary, components, operations, production)
        if production.state == 'done':
            res['total_mo_cost'] += production.extra_cost * summary['quantity']
        return res

    def _get_replenishment_lines(self, production, move_raw, replenish_data, level, current_index):
        res = super()._get_replenishment_lines(production, move_raw, replenish_data, level, current_index)
        quantity = move_raw.product_uom_qty if move_raw.state != 'done' else move_raw.quantity
        for replenishment in res:
            if replenishment['summary']['model'] == 'mrp.production':
                production = self.env['mrp.production'].browse(replenishment['summary']['id'])
                self._update_summary_with_extra_cost_values(replenishment['summary'], production, quantity)
        return res

    def _update_summary_with_extra_cost_values(self, summary, production, quantity):
        if production:
            summary['extra_cost'] = production.extra_cost
            summary['price_precision'] = self.env['decimal.precision'].precision_get('Product Price')
            summary['product_precision'] = self.env['decimal.precision'].precision_get('Product Unit')
            summary['mo_cost'] += production.extra_cost * summary['quantity'] * self._get_remaining_cost_share(production)
        return summary

    def _get_unit_cost(self, move):
        if move.state == 'done':
            price_unit = move._get_price_unit()
            return move.product_id.uom_id._compute_price(price_unit, move.uom_id)
        return super()._get_unit_cost(move)
