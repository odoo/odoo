# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ProductTag(models.Model):
    _name = 'product.tag'
    _inherit = ['website.multi.mixin', 'product.tag']

    visible_on_ecommerce = fields.Boolean(
        string="Visible on eCommerce",
        help="Whether the tag is displayed on the eCommerce.",
        default=True,
    )
    image = fields.Image(string="Image", max_width=200, max_height=200)
