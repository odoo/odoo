# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    def write(self, vals):
        invalidate = "sequence" in vals and any(
            record.sequence != vals["sequence"] for record in self
        )

        res = super().write(vals)

        if invalidate:
            templates = self.mapped("pav_attribute_line_ids.product_tmpl_id")
            templates._update_images_type()

        return res
