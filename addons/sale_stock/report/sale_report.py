# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)

    def _group_by_sale(self, groupby=''):
        res = super()._group_by_sale(groupby)
        res += """,s.warehouse_id"""
        return res

    def _select_additional_fields(self, fields):
        fields['warehouse_id'] = ", s.warehouse_id as warehouse_id"
        return super()._select_additional_fields(fields)
