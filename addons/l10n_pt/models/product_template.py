from odoo import models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, vals):
        if self.env.company.account_fiscal_country_id.code != 'PT':
            return super().write(vals)
        for product in self:
            if 'name' in vals:
                account_move_lines_count = self.env['account.move.line'].search_count([('product_id', 'in', product.product_variant_ids.ids)])
                if account_move_lines_count:
                    raise UserError(_("You cannot change the name of a product that is already used in invoices."))
        return super().write(vals)
