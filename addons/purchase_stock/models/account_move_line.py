# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.float_utils import float_is_zero
from collections import defaultdict


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_price_unit_val_dif_and_relevant_qty(self):
        self.ensure_one()

        # Valuation_price unit is always expressed in invoice currency, so that it can always be computed with the good rate
        valuation_price_unit = self.product_id.uom_id._compute_price(self.product_id.standard_price, self.product_uom_id)
        valuation_price_unit = -valuation_price_unit if self.move_id.move_type == 'in_refund' else valuation_price_unit
        valuation_date = self.date
        valuation_price_unit = self.company_currency_id._convert(
            valuation_price_unit,
            self.currency_id, self.company_id, valuation_date, round=False
        )

        price_unit = self._get_gross_unit_price()

        price_unit_val_dif = price_unit - valuation_price_unit
        # If there are some valued moves, we only consider their quantity already used
        relevant_qty = self.quantity

        return price_unit_val_dif, relevant_qty
<<<<<<< 441fe49cf07ed32e50baba08f62c2b1cf7f7fff8

    def _get_stock_moves(self):
        return super()._get_stock_moves() | self.purchase_line_id.move_ids
||||||| 2080b7d78380585430147845a64d94321a3d5da4
=======

    def _related_analytic_distribution(self):
        # EXTENDS 'account'
        vals = super()._related_analytic_distribution()
        if not self.purchase_line_id and not self.analytic_distribution and self.move_id.stock_move_id.purchase_line_id:
            vals |= self.move_id.stock_move_id.purchase_line_id.analytic_distribution or {}
        return vals
>>>>>>> e83acd214f8633f21b4cfa76082cb1b7001ae2eb
