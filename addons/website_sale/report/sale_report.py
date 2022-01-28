# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    website_id = fields.Many2one('website', readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['website_id'] = "s.website_id"
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            s.website_id"""
        return res
