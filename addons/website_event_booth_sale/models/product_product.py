# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('is_event_booth')
    def _compute_hide_from_shop(self):
        super()._compute_hide_from_shop()
        for product in self:
            product.hide_from_shop = product.hide_from_shop or product.is_event_booth

    def _is_add_to_cart_allowed(self):
        # `event_booth_registration_confirm` calls `_cart_update` with specific products, allow those aswell.
        return super()._is_add_to_cart_allowed() or\
                self.env['event.booth.category'].sudo().search_count([('product_id', '=', self.id)])

    def _is_allow_zero_price(self):
        return super()._is_allow_zero_price() or self.is_event_booth
