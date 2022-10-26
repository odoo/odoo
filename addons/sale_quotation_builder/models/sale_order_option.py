# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleOrderOption(models.Model):
    _inherit = "sale.order.option"

    website_description = fields.Html(
        string="Website Description",
        compute='_compute_website_description',
        store=True, readonly=False, precompute=True,
        sanitize_overridable=True,
        sanitize_attributes=False, translate=html_translate)

    @api.depends('product_id')
    def _compute_website_description(self):
        for option in self:
            if not option.product_id:
                continue
            product = option.product_id.with_context(lang=option.order_id.partner_id.lang)
            option.website_description = product.quotation_description

    def _get_values_to_add_to_order(self):
        values = super()._get_values_to_add_to_order()
        values.update(website_description=self.website_description)
        return values
