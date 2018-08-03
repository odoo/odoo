# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.translate import html_translate


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # hack, if website_sale is not installed, we need website_description to exist (and then it will be empty)
    # website_description = fields.Html('Description for the website', sanitize_attributes=False, translate=html_translate)
    quote_description = fields.Html('Description for the quote', sanitize_attributes=False, translate=html_translate)

    def get_quote_description_or_website_description(self):
        if self.quote_description:
            return self.quote_description
        if self.__class__.website_description and self.website_description:
            return self.website_description
        return ''
