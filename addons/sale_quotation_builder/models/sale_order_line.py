# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    website_description = fields.Html(
        string="Website Description",
        compute='_compute_website_description',
        store=True, readonly=False, precompute=True,
        sanitize_overridable=True,
        translate=html_translate,
        sanitize_attributes=False)

    @api.depends('product_id')
    def _compute_website_description(self):
        for line in self:
            if not line.product_id:
                continue
            line.website_description = line.product_id.with_context(
                lang=line.order_partner_id.lang
            ).quotation_description
