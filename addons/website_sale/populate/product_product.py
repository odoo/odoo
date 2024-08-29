# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import product

from odoo import models
from odoo.tools import populate


class ProductProduct(models.Model, product.ProductProduct):

    def _populate_get_product_factories(self):
        """Populate the invoice_policy of product.product & product.template models."""
        return super()._populate_get_product_factories() + [
            ('is_published', populate.randomize([True, False], [8, 2]))]
