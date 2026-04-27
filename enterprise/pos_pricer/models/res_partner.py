from odoo import models

class PricerResPartner(models.Model):
    _inherit = 'res.partner'

    def write(self, vals):
        res = super().write(vals)

        # If we change the supplier reference update Pricer tags
        if ('ref' in vals):
            # Note: res.partner does not have a One2many field for 'product.supplierinfo'
            products = self.env['product.supplierinfo'].search([('partner_id', '=', self.id)]).mapped('product_id')
            products.sudo().write({'pricer_product_to_create_or_update': True})

        return res
