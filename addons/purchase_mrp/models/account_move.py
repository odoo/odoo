# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_stock_valuation_layers_price_unit(self, move, layers, previous_invoices_price, previous_invoices_quantity):
        if self.product_id == layers.product_id:
            return super()._get_stock_valuation_layers_price_unit()
        total_prices = sum(layers.mapped('value')) - previous_invoices_price
        total_quantity = self.purchase_line_id.qty_received - previous_invoices_quantity
        if not total_quantity:
            return 0
        return total_prices / total_quantity
