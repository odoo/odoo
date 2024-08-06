# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    website_id = fields.Many2one('website', readonly=True)

    def _group_by_sale(self, groupby=''):
        res = super()._group_by_sale(groupby)
        res += """,s.website_id"""
        return res

    def _select_additional_fields(self, fields):
        fields['website_id'] = ", s.website_id as website_id"
        return super()._select_additional_fields(fields)
