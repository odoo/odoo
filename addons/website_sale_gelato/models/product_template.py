# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # === CONSTRAINT METHODS === #

    @api.constrains('is_published')
    def _check_print_images_are_set_before_publishing(self):
        for product in self.filtered('gelato_template_ref'):
            if product.is_published and product.gelato_missing_images:
                raise ValidationError(
                    _("Print images must be set on products before they can be published.")
                )

    # === ACTION METHODS === #

    def action_create_product_variants_from_gelato_template(self):
        """ Override of `sale_gelato` to unpublish products for which the synchronization with
        Gelato led to new print images being created. """
        image_count_before_sync = len(self.gelato_image_ids)
        res = super().action_create_product_variants_from_gelato_template()
        if image_count_before_sync < len(self.gelato_image_ids):
            self.is_published = False
        return res

    # === BUSINESS METHODS === #

    def _create_attributes_from_gelato_info(self, template_info):
        """ Override of `sale_gelato` to set the eCommerce description. """
        self.description_ecommerce = template_info['description']
        return super()._create_attributes_from_gelato_info(template_info)
