from collections import OrderedDict

from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _prepare_categories_for_display(self):
        attributes = self.product_tmpl_id.valid_product_template_attribute_line_ids.attribute_id.sorted()
        categories = OrderedDict(
            [(cat, OrderedDict()) for cat in attributes.category_id.sorted()]
        )
        if any(not pa.category_id for pa in attributes):
            categories[self.env["product.attribute.category"]] = OrderedDict()
        for pa in attributes:
            categories[pa.category_id][pa] = OrderedDict(
                [
                    (
                        product,
                        product.product_template_attribute_value_ids.filtered(
                            lambda ptav, pa=pa: ptav.attribute_id == pa
                        )
                        or product.attribute_line_ids.filtered(
                            lambda ptal, pa=pa: ptal.attribute_id == pa
                        ).value_ids,
                    )
                    for product in self
                ]
            )
        _debug.pipeline(
            "comparison_categories",
            products=self,
            attributes=attributes,
            categories=len(categories),
            uncategorised=any(not pa.category_id for pa in attributes),
        )
        return categories

    def _get_image_1024_url(self):
        self.check_singleton()
        return self.env["website"].image_url(self, "image_1024")
