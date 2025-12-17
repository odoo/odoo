# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class SaleReport(models.Model):
    _inherit = 'sale.report'

    margin = fields.Float('Margin')

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['margin'] = SQL(
            "SUM(l.margin / %s * %s)",
            self._case_value_or_one(SQL.identifier('s', 'currency_rate')),
            self._case_value_or_one(SQL.identifier('account_currency_table', 'rate')),
        )
        return res
