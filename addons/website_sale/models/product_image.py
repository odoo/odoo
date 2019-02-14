# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProductImage(models.Model):
    _name = 'product.image'
    _description = "Product Image"
    _inherit = ['image.mixin']
    _order = 'sequence, id'

    name = fields.Char("Name", required=True)
    sequence = fields.Integer(default=10, index=True)

    image_original = fields.Binary(required=True)

    product_tmpl_id = fields.Many2one('product.template', "Product Template", index=True, ondelete='cascade')
    product_variant_id = fields.Many2one('product.product', "Product Variant", index=True, ondelete='cascade')
