from odoo import models

class AccountTax(models.Model):
    _inherit = 'account.tax'
    
    def write(self, vals):
        res = super().write(vals)

        # If we change the taxes name, update Pricer tags with the new name
        if ('name' in vals):
            products = self.env['product.template'].search([
                ('taxes_id', 'in', self.ids)
            ])
            if products:
                products.mapped('product_variant_id').write({'pricer_product_to_create_or_update': True})

        return res
