# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import models, fields


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    visibility = fields.Selection([('visible', 'Visible'), ('hidden', 'Hidden')], default='visible')


class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    def _prepare_single_value_for_display(self):
        """On the product page group together the attribute lines that concern
        the same attribute and that have only one value each.

        Indeed those are considered informative values, they do not generate
        choice for the user, so they are displayed below the configurator.

        The returned attributes are ordered as they appear in `self`, so based
        on the order of the attribute lines.
        """
        single_value_lines = self.filtered(lambda ptal: len(ptal.value_ids) == 1)
        single_value_attributes = OrderedDict([(pa, self.env['product.template.attribute.line']) for pa in single_value_lines.attribute_id])
        for ptal in single_value_lines:
            single_value_attributes[ptal.attribute_id] |= ptal
        return single_value_attributes

class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    def is_product_variant_in_category(self, category):
        # All products category
        if(not category.name):
            return True
        # Specific category
        for child in category.child_id:
            if(self.is_product_variant_in_category(child)):
                return True
        attributes_products = self.pav_attribute_line_ids.product_tmpl_id
        # Check if at least one element of this attribute value is displayed in the selected category
        return any(product in attributes_products for product in category.product_tmpl_ids)
