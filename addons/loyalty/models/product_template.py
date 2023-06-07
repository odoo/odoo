# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_loyalty_products(self):
        product_data = [
            self.env.ref('loyalty.gift_card_product_50', False),
            self.env.ref('loyalty.ewallet_product_50', False),
        ]
        for product in self.filtered(lambda p: p.product_variant_id in product_data):
            raise UserError(_(
                "You cannot delete %(name)s as it is used in 'Coupons & Loyalty'."
                " Please archive it instead.",
                name=product.name
            ))
