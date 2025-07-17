# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import models


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
        attributes = self.product_tmpl_id.valid_product_template_attribute_line_ids.attribute_id.sorted()
        categories = OrderedDict([(cat, OrderedDict()) for cat in attributes.category_id.sorted()])
        if any(not pa.category_id for pa in attributes):
            # category_id is not required and the mapped does not return empty
            categories[self.env['product.attribute.category']] = OrderedDict()
        for pa in attributes:
            categories[pa.category_id][pa] = OrderedDict([(
                product,
                product.product_template_attribute_value_ids.filtered(
                    lambda ptav: ptav.attribute_id == pa
                ) or  # If no_variant, show all possible values
                product.attribute_line_ids.filtered(lambda ptal: ptal.attribute_id == pa).value_ids
            ) for product in self])
        return categories

    def _get_image_1024_url(self):
        """ Returns the local url of the product main image.
        Note: self.ensure_one()
        :rtype: str
        """
        self.ensure_one()
        return self.env['website'].image_url(self, 'image_1024')
