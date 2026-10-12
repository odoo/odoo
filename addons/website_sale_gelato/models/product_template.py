# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # === CONSTRAINT METHODS === #

    @api.constrains("is_published")
    def _check_print_images_are_set_before_publishing(self):
        for product in self.filtered("gelato_template_ref"):
            if product.is_published and product.gelato_missing_images:
                raise ValidationError(
                    self.env._("Print images must be set on products before they can be published.")
                )

    # === BUSINESS METHODS === #

    def _create_attributes_from_gelato_info(self, template_info):
        """Override of `sale_gelato` to set the eCommerce description."""
        self.description_ecommerce = template_info["description"]
        return super()._create_attributes_from_gelato_info(template_info)
