# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        order_lines = super().create(vals_list)
        order_lines.order_id._prevent_mixing_gelato_and_non_gelato_products()
        return order_lines

    def write(self, vals):
        res = super().write(vals)
        self.order_id._prevent_mixing_gelato_and_non_gelato_products()
        return res
