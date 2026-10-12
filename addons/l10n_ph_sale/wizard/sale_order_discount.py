# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderDiscount(models.TransientModel):
    _inherit = "sale.order.discount"

    def _get_discountable_order_lines(self):
        # SC/PWD privileged lines are managed exclusively by the discount
        # privilege wizard and must never be (double-)discounted here.
        return super()._get_discountable_order_lines().filtered(
            lambda line: not line.l10n_ph_discount_privilege_id,
        )
