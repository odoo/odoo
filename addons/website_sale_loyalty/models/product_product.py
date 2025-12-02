# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _can_return_content(self, field_name=None, access_token=None):
        """ Override of `orm` to give public users access to the unpublished product image.

        Give access to the public users to the unpublished product images if they are linked to a
        reward.

        :param field_name: The name of the field to check.
        :param access_token: The access token.
        :return: Whether to allow the access to the image.
        :rtype: bool
        """
        if (
            field_name in ["image_%s" % size for size in [1920, 1024, 512, 256, 128]]
            and self.env['loyalty.reward'].sudo().search_count([
                ('discount_line_product_id', '=', self.id),
            ], limit=1)
        ):
            return True
        return super()._can_return_content(field_name, access_token)

    def _get_product_placeholder_filename(self):
        """ Override of `product` to set a default image for reward products. """
        # In sudo mode to allow eCommerce customers to see the placeholder
        if self.env['loyalty.reward'].sudo().search_count([
            ('discount_line_product_id', '=', self.id),
        ], limit=1):
            if self.env['loyalty.reward'].sudo().search_count([
                ('program_type', '=', 'gift_card'),
                ('discount_line_product_id', '=', self.id),
            ], limit=1):
                return 'loyalty/static/img/gift_card.png'
            return 'loyalty/static/img/discount_placeholder_thumbnail.png'
        return super()._get_product_placeholder_filename()
