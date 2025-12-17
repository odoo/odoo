# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import models


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
        single_value_lines = self.filtered(
            lambda ptal: len(ptal.value_ids) == 1 and ptal.attribute_id.display_type != 'multi'
        )
        single_value_attributes = OrderedDict([(pa, self.env['product.template.attribute.line']) for pa in single_value_lines.attribute_id])
        for ptal in single_value_lines:
            single_value_attributes[ptal.attribute_id] |= ptal
        return single_value_attributes

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
