# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    margin = fields.Float('Margin')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['margin'] = ", SUM(l.margin / COALESCE(cr.rate, 1.0)) AS margin"
        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)
