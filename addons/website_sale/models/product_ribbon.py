# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class ProductRibbon(models.Model):
    _name = "product.ribbon"
    _description = 'Product ribbon'

    @api.depends('html')
    def _compute_display_name(self):
        for ribbon in self:
            ribbon.display_name = f'{tools.html2plaintext(ribbon.html)} (#{ribbon.id})'

    html = fields.Html(string='Ribbon html', required=True, translate=True, sanitize=False)
    bg_color = fields.Char(string='Ribbon background color', required=False)
    text_color = fields.Char(string='Ribbon text color', required=False)
    html_class = fields.Char(string='Ribbon class', required=True, default='')
