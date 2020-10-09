from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _populate_get_types(self):
        # Ensure database population generates some storable products.
        types, weights = super()._populate_get_types()
        return types+["product"], weights+[2]
