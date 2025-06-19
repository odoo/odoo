from odoo import models


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def action_archive(self):
        loyalty_programs = self.env['loyalty.program'].search([('pricelist_ids', 'in', self.ids)])
        loyalty_programs.pricelist_ids = False
        return super().action_archive()
