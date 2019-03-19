# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class ProductTemplate(models.Model):
    _inherit = ['product.template']

    @api.multi
    def _is_quick_add_to_cart_possible(self, parent_combination=None):
        quick_add_possible = super(ProductTemplate, self)._is_quick_add_to_cart_possible(parent_combination)

        if not quick_add_possible:
            return quick_add_possible

        if self.optional_product_ids.filtered(lambda p: p._is_add_to_cart_possible(self._get_first_possible_combination())):
            return False
        return True
