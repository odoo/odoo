# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleOrderTemplateLine(models.Model):
    _inherit = 'sale.order.template.line'

    # FIXME ANVFE why are the sanitize_* attributes different between this field
    # and the one on option lines, doesn't make any sense ???
    website_description = fields.Html(
        string="Website Description",
        compute='_compute_website_description',
        store=True, readonly=False,
        translate=html_translate,
        sanitize_overridable=True,
        sanitize_form=False)

    @api.depends('product_id')
    def _compute_website_description(self):
        for line in self:
            if not line.product_id:
                continue
            line.website_description = line.product_id.quotation_description

    #=== BUSINESS METHODS ===#

    def _prepare_order_line_values(self):
        res = super()._prepare_order_line_values()
        res['website_description'] = self.website_description
        return res
