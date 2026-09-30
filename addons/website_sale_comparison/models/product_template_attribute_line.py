# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import models


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

    def _prepare_categories_for_display_in_specs_table(self):
        """
         Prepare attribute categories for display in a specs table.

        Filters out attribute lines that have a single value and whose value is
        marked as custom, then call _prepare_categories_for_display to group
        the remaining attribute lines by category.

        :return: OrderedDict [{
        product.attribute.category: [product.template.attribute.line]
        }]
        """
        filtered_self = self - self.filtered(
            lambda ptal: len(ptal.value_ids) == 1 and ptal.value_ids.is_custom
        )
        return filtered_self._prepare_categories_for_display()
