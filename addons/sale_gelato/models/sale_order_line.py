# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        order_lines = super().create(vals_list)
        order_lines.order_id._prevent_mixing_gelato_and_non_gelato_products()
        order_lines._prevent_buying_unconfigured_gelato_products()
        return order_lines

    def write(self, vals):
        res = super().write(vals)
        self.order_id._prevent_mixing_gelato_and_non_gelato_products()
        self._prevent_buying_unconfigured_gelato_products()
        return res

    def _prevent_buying_unconfigured_gelato_products(self):
        """Prevent buying Gelato products that are missing print images.

        :rtype: None
        :raise ValidationError: If a Gelato product is missing print images.
        """
        if any(line.product_id.product_tmpl_id.gelato_missing_images for line in self):
            raise ValidationError(_("You cannot order unconfigured Gelato products."))
