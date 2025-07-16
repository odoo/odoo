# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import ValidationError


class ProductDocument(models.Model):
    _inherit = 'product.document'

    # === CONSTRAINT METHODS === #

    @api.constrains('datas')
    def _check_product_is_unpublished_before_removing_print_images(self):
        gelato_product_tmpl_images = self.filtered(
            lambda i: i.is_gelato and i.res_model == 'product.template'
        )
        for print_image in gelato_product_tmpl_images:
            template = self.env['product.template'].browse(print_image.res_id)
            if template.is_published and not print_image.datas:
                raise ValidationError(
                    _("Products must be unpublished before print images can be removed.")
                )
