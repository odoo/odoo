# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    blog_post_ids = fields.Many2many(
        'blog.post',
        'product_blogpost_rel',
        string="Blog Posts",
        help="Blog Posts that promote this product.",
    )


class BlogPost(models.Model):
    _inherit = "blog.post"

    product_ids = fields.Many2many(
        'product.template',
        'product_blogpost_rel',
        string="Products",
        help="Products promoted by this blog post",
    )
