from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    price_unit = fields.Float(
        'Unit Price', compute='_compute_standard_price', store=False)

    def _compute_standard_price(self):

        try:
            self.price_unit = 200
            self.standard_price = self.marketplace_product.unit_price
        except Exception as exc1:
            print(exc1)

        self.price_unit = 200
        self.standard_price = 200