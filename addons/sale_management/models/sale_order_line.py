# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _description = "Sales Order Line"

    sale_order_option_ids = fields.One2many('sale.order.option', 'line_id', 'Optional Products Lines')

    @api.depends('product_id')
    def _compute_name(self):
        # Take the description on the order template if the product is present in it
        super()._compute_name()
        for line in self:
            if line.product_id and line.order_id.sale_order_template_id:
                for template_line in line.order_id.sale_order_template_id.sale_order_template_line_ids:
                    if line.product_id == template_line.product_id:
                        lang = line.order_id.partner_id.lang
                        line.name = template_line.with_context(lang=lang).name + line.with_context(lang=lang)._get_sale_order_line_multiline_description_variants()
                        break

    def _compute_price_unit(self):
        # Avoid recomputing the price with pricelist rules, use the initial price
        # used in the optional product line.
        optional_product_lines = self.filtered('sale_order_option_ids')
        super(SaleOrderLine, self - optional_product_lines)._compute_price_unit()
