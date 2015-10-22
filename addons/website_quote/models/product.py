# -*- coding: utf-8 -*-
from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    website_description = fields.Html(string='Description for the website')  # hack, if website_sale is not installed
    quote_description = fields.Html(string='Description for the quote')
