# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import sale_margin, pos_sale


class SaleReport(pos_sale.SaleReport, sale_margin.SaleReport):

    def _fill_pos_fields(self, additional_fields):
        values = super()._fill_pos_fields(additional_fields)
        values['margin'] = 'SUM(l.price_subtotal - COALESCE(l.total_cost,0) / CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END)'
        return values
