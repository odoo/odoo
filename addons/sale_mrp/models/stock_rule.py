# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_product_description_variants_lang(self, values):
        res = super()._get_product_description_variants_lang(values)
        sale_line_id = values.get("sale_line_id")
        if sale_line_id:
            res = self.env["sale.order.line"].browse(sale_line_id).order_id.partner_id.lang
        return res
