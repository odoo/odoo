from odoo import models


class PricerProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, vals):
        """
        Called whenever we update a product template price and click "save"
        We need to update all the products variants
        """
        if 'list_price' in vals:
            for record in self:
                for product in record.product_variant_ids:
                    product.pricer_product_to_create_or_update = True

        return super().write(vals)
