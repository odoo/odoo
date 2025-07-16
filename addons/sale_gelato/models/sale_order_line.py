# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        order_lines = super().create(vals_list)

        for order_line in order_lines:
            if order_line.product_id.product_tmpl_id.gelato_missing_images:
                raise ValidationError(_('You cannot add unconfigured Gelato product to the order.'))

        order_lines.order_id._prevent_mixing_gelato_and_non_gelato_products()
        return order_lines

    def write(self, vals):
        res = super().write(vals)

        if any(template.gelato_missing_images for template in self.product_id.product_tmpl_id):
            raise ValidationError(_('You cannot add unconfigured Gelato product to the order.'))

        self.order_id._prevent_mixing_gelato_and_non_gelato_products()
        return res
