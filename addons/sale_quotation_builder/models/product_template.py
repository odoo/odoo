# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools.translate import html_translate


class ProductTemplate(models.Model):
    _inherit = "product.template"

    quotation_only_description = fields.Html('Quotation Only Description', sanitize_attributes=False,
        translate=html_translate, help="The quotation description (not used on eCommerce)")

    quotation_description = fields.Html('Quotation Description', compute='_compute_quotation_description',
        help="This field uses the Quotation Only Description if it is defined, otherwise it will try to read the eCommerce Description.")

    def _compute_quotation_description(self):
        for record in self:
            if record.quotation_only_description:
                record.quotation_description = record.quotation_only_description
            elif hasattr(record, 'website_description') and record.website_description:
                record.quotation_description = record.website_description
            else:
                record.quotation_description = ''
