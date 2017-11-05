# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    optional_product_ids = fields.Many2many('product.template', 'product_optional_rel', 'src_id', 'dest_id',
                                            string='Optional Products', help="Optional Products are suggested "
                                            "whenever the customer hits *Add to Cart* (cross-sell strategy, "
                                            "e.g. for computers: warranty, software, etc.).")
