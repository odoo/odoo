# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.translate import html_translate


class ProductTemplate(models.Model):
    _inherit = "product.template"

    quote_description = fields.Html('Description for the quote', sanitize_attributes=False, translate=html_translate)

    def get_quote_description_or_website_description(self):
        if self.quote_description:
            return self.quote_description
        if hasattr(self, 'website_description') and self.website_description:
            return self.website_description
        return ''


class ProductProduct(models.Model):
    _inherit = "product.product"

    def get_quote_description_or_website_description(self):
        return self.product_tmpl_id.get_quote_description_or_website_description()
