# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleOrderTemplateOption(models.Model):
    _inherit = 'sale.order.template.option'

    website_description = fields.Html(
        string="Website Description",
        compute='_compute_website_description',
        store=True, readonly=False,
        translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False)

    @api.depends('product_id')
    def _compute_website_description(self):
        for option in self:
            if not option.product_id:
                continue
            option.website_description = option.product_id.quotation_description

    #=== BUSINESS METHODS ===#

    def _prepare_option_line_values(self):
        res = super()._prepare_option_line_values()
        res['website_description'] = self.website_description
        return res
