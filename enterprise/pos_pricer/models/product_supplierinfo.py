from odoo import models

class PricerProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    def write(self, vals):
        res = super().write(vals)

        # If we change the supplier product reference, update Pricer tags
        if ('product_code' in vals):
            self.mapped('product_id').sudo().write({'pricer_product_to_create_or_update': True})

        return res
