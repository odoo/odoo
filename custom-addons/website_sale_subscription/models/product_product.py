# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _website_can_be_added(self, so=None, pricelist=None, pricing=None, product=None):
        return self.product_tmpl_id._website_can_be_added(so, pricelist, pricing, product or self)

    def _website_show_quick_add(self):
        self.ensure_one()
        return super()._website_show_quick_add() and self._website_can_be_added(product=self)

    def _is_add_to_cart_allowed(self):
        self.ensure_one()
        return super()._is_add_to_cart_allowed() and self._website_can_be_added(product=self)
