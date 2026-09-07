# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReportMrpReport_Mo_Overview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _get_report_data(self, production_id):
        res = super()._get_report_data(production_id)
        production = self.env['mrp.production'].browse(production_id)
        self._update_summary_with_extra_cost_values(res['summary'], production, res['summary']['quantity'])
        total_extra_cost = production.extra_cost * res['summary']['quantity']
        res['extras']['unit_mo_cost'] += production.extra_cost
        res['extras']['unit_bom_cost'] += production.extra_cost
        res['extras']['unit_real_cost'] += total_extra_cost
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
            summary['bom_cost'] += production.extra_cost
            summary['mo_cost'] += production.extra_cost
            summary['real_cost'] += production.extra_cost * quantity
        return summary

    def _get_unit_cost(self, move):
        if move.state == 'done':
            price_unit = move._get_price_unit()
            return move.product_id.uom_id._compute_price(price_unit, move.uom_id)
        return super()._get_unit_cost(move)
