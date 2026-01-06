# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _is_in_wishlist(self):
        self.ensure_one()
        return self in self.env['product.wishlist'].current().mapped('product_id.product_tmpl_id')
