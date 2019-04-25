# -*- coding: utf-8 -*-
from collections import OrderedDict

from odoo import fields, models, _


class ProductAttributeCategory(models.Model):
    _name = "product.attribute.category"
    _description = "Product Attribute Category"
    _order = 'sequence'

    name = fields.Char("Category Name", required=True)
    sequence = fields.Integer("Sequence", default=10)


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    category_id = fields.Many2one('product.attribute.category', string="Category",
                                  help="Set a category to regroup similar attributes under "
                                  "the same section in the Comparison page of eCommerce")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def get_variant_groups(self):
        res = OrderedDict()
        for var in self.attribute_line_ids.sorted(lambda x: x.attribute_id.sequence):
            res.setdefault(var.attribute_id.category_id.name or _('Uncategorized'), []).append(var)
        return res
