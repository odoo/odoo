# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    optional_product_ids = fields.Many2many('product.template', 'product_optional_rel', 'src_id', 'dest_id',
                                            string='Optional Products', help="Suggest optional products when adding the product to a cart.")
