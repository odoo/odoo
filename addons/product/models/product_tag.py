# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from random import randint

from odoo import api, fields, models
from odoo.osv import expression

class ProductTag(models.Model):
    _name = 'product.tag'
    _description = 'Product Tag'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color', default=_get_default_color)

    product_template_ids = fields.Many2many('product.template', 'product_tag_product_template_rel')
    product_product_ids = fields.Many2many('product.product', 'product_tag_product_product_rel')
    product_ids = fields.Many2many(
        'product.product', string='All Product Variants using this Tag',
        compute='_compute_product_ids', search='_search_product_ids'
    )

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]

    @api.depends('product_template_ids', 'product_product_ids')
    def _compute_product_ids(self):
        for tag in self:
            tag.product_ids = tag.product_template_ids.product_variant_ids | tag.product_product_ids

    def _search_product_ids(self, operator, operand):
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            return [('product_template_ids.product_variant_ids', operator, operand), ('product_product_ids', operator, operand)]
        return ['|', ('product_template_ids.product_variant_ids', operator, operand), ('product_product_ids', operator, operand)]
