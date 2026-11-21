# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _is_purchase_return(self):
        res = super()._is_purchase_return()
        return res or self._is_subcontract_return()

    def _get_price_unit_receipt_value(self, order, convert_date):
        """ A subcontracted receipt is not valued: its value lives on the finished
        move of the production. Only the part above the consumed components comes
        from the purchase order line (the subcontracting service)."""
        receipt_value = super()._get_price_unit_receipt_value(order, convert_date)
        productions = self.sudo().filtered(
            lambda m: m.is_subcontract and m.state == 'done',
        ).move_orig_ids.production_id.filtered(lambda p: p.state == 'done')
        if not productions:
            return receipt_value
        finished_layers = productions.move_finished_ids.filtered(
            lambda m: m.product_id == m.production_id.product_id,
        ).sudo().stock_valuation_layer_ids.filtered(lambda layer: layer._should_impact_price_unit_receipt_value())
        components_value = -sum(productions.move_raw_ids.sudo().stock_valuation_layer_ids.mapped('value'))
        service_value = sum(finished_layers.mapped('value')) - components_value
        return receipt_value + order.company_id.currency_id._convert(
            service_value, order.currency_id, order.company_id, convert_date, round=False)
