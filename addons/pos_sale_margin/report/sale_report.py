# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleReport(models.Model):
    _inherit = "sale.report"

    def _fill_pos_fields(self, additional_fields):
        values = super()._fill_pos_fields(additional_fields)
        values['margin'] = 'SUM((SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal) - COALESCE(l.total_cost, 0)) / CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END)'
        values['margin_percent'] = 'MAX(CASE COALESCE(SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal), 0) WHEN 0 THEN 0 ELSE (SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal) - COALESCE(l.total_cost, 0)) / (SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal)) END)'
        values['purchase_price'] = 'SUM(l.total_cost / CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END)'
        return values
