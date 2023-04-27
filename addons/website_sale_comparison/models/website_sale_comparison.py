# -*- coding: utf-8 -*-

from collections import OrderedDict

from odoo import fields, models


class ProductAttributeCategory(models.Model):
    _name = "product.attribute.category"
    _description = "Product Attribute Category"
    _order = 'sequence, id'

    name = fields.Char("Category Name", required=True, translate=True)
    sequence = fields.Integer("Sequence", default=10, index=True)

    attribute_ids = fields.One2many('product.attribute', 'category_id', string="Related Attributes", domain="[('category_id', '=', False)]")


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'
    _order = 'category_id, sequence, id'

    category_id = fields.Many2one('product.attribute.category', string="Category", index=True,
                                  help="Set a category to regroup similar attributes under "
                                  "the same section in the Comparison page of eCommerce")


class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    def _prepare_categories_for_display(self):
        """On the product page group together the attribute lines that concern
        attributes that are in the same category.

        The returned categories are ordered following their default order.

        :return: OrderedDict [{
            product.attribute.category: [product.template.attribute.line]
        }]
        """
        attributes = self.attribute_id
        categories = OrderedDict([(cat, self.env['product.template.attribute.line']) for cat in attributes.category_id.sorted()])
        if any(not pa.category_id for pa in attributes):
            # category_id is not required and the mapped does not return empty
            categories[self.env['product.attribute.category']] = self.env['product.template.attribute.line']
        for ptal in self:
            categories[ptal.attribute_id.category_id] |= ptal
        return categories


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _prepare_categories_for_display(self):
        """On the comparison page group on the same line the values of each
        product that concern the same attributes, and then group those
        attributes per category.

        The returned categories are ordered following their default order.

        :return: OrderedDict [{
            product.attribute.category: OrderedDict [{
                product.attribute: OrderedDict [{
                    product: [product.template.attribute.value]
                }]
            }]
        }]
        """
        attributes = self.product_tmpl_id.valid_product_template_attribute_line_ids._without_no_variant_attributes().attribute_id.sorted()
        categories = OrderedDict([(cat, OrderedDict()) for cat in attributes.category_id.sorted()])
        if any(not pa.category_id for pa in attributes):
            # category_id is not required and the mapped does not return empty
            categories[self.env['product.attribute.category']] = OrderedDict()
        for pa in attributes:
            categories[pa.category_id][pa] = OrderedDict([(
                product,
                product.product_template_attribute_value_ids.filtered(lambda ptav: ptav.attribute_id == pa)
            ) for product in self])

        return categories
