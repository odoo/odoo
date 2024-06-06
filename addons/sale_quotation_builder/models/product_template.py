# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.translate import html_translate


class ProductTemplate(models.Model):
    _inherit = "product.template"

    quotation_only_description = fields.Html(
        string="Quotation Only Description",
        translate=html_translate,
        sanitize_attributes=False,
        sanitize_overridable=True,
        help="The quotation description (not used on eCommerce)")

    quotation_description = fields.Html(
        string="Quotation Description",
        compute='_compute_quotation_description',
        sanitize_attributes=False,
        sanitize_overridable=True,
        help="This field uses the Quotation Only Description if it is defined, "
             "otherwise it will try to read the eCommerce Description.")

    def _compute_quotation_description(self):
        for template in self:
            if template.quotation_only_description:
                template.quotation_description = template.quotation_only_description
            elif hasattr(template, 'website_description') and template.website_description:
                # Defined in website_sale
                template.quotation_description = template.website_description
            else:
                template.quotation_description = ''
