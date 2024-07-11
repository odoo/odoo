# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _is_add_to_cart_allowed(self):
        # `event_booth_registration_confirm` calls `_cart_update` with specific products, allow those aswell.
        return super()._is_add_to_cart_allowed() or\
                self.env['event.booth.category'].sudo().search_count([('product_id', '=', self.id)])
