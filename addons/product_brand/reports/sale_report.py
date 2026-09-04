# Copyright 2018 Tecnativa - David Vidal
# Copyright 2020 Tecnativa - João Marques
# Copyright 2022 NuoBiT - Eric Antones
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    product_brand_id = fields.Many2one(comodel_name="product.brand", string="Brand")

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res["product_brand_id"] = "t.product_brand_id"
        return res

    def _group_by_sale(self):
        group_by = super()._group_by_sale()
        group_by = f"""
            {group_by},
            t.product_brand_id"""
        return group_by
