from odoo import _, models
from odoo.exceptions import UserError


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def action_archive(self):
        loyalty_programs = self.env['loyalty.program'].sudo().search([
            ('active', '=', True),
            ('pricelist_ids', 'in', self.ids)
        ])
        if loyalty_programs:
            raise UserError(_(
                "This pricelist may not be archived. "
                "It is being used for active promotion programs: %s",
                ', '.join(loyalty_programs.mapped('name'))
            ))
        return super().action_archive()
