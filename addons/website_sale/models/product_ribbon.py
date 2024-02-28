# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class ProductRibbon(models.Model):
    _name = "product.ribbon"
    _description = 'Product ribbon'

    def name_get(self):
        return [(ribbon.id, '%s (#%d)' % (tools.html2plaintext(ribbon.html), ribbon.id)) for ribbon in self]

    html = fields.Html(string='Ribbon html', required=True, translate=True, sanitize=False)
    bg_color = fields.Char(string='Ribbon background color', required=False)
    text_color = fields.Char(string='Ribbon text color', required=False)
    html_class = fields.Char(string='Ribbon class', required=True, default='')
    product_tag_ids = fields.One2many('product.tag', 'ribbon_id', string='Product Tags')
