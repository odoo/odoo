# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleReport(models.Model):
    _inherit = "sale.report"

    def _select_pos(self, fields=None):
        if not fields:
            fields = {}
        fields['margin'] = ', SUM(l.price_subtotal - l.total_cost / CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END) AS margin'
        return super()._select_pos(fields)
