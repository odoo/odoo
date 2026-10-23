# Copyright 2018 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    product_brand_id = fields.Many2one(
        comodel_name='product.brand',
        string='Brand',
    )

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['product_brand_id'] = "t.product_brand_id"
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            t.product_brand_id"""
        return res
