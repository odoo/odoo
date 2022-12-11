# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)

<<<<<<< HEAD
    def _group_by_sale(self, groupby=''):
        res = super()._group_by_sale(groupby)
        res += """,s.warehouse_id"""
        return res

    def _select_additional_fields(self, fields):
||||||| parent of 7c06da498ff (temp)
    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
=======
    def _group_by_sale(self, groupby=''):
        res = super()._group_by_sale(groupby)
        res += """, s.warehouse_id"""
        return res

    def _select_additional_fields(self, fields):
>>>>>>> 7c06da498ff (temp)
        fields['warehouse_id'] = ", s.warehouse_id as warehouse_id"
        return super()._select_additional_fields(fields)
