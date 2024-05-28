from odoo import models, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = ['account.account']

    def write(self, vals):
        if 'DE' in self.company_id.account_fiscal_country_id.mapped('code') and ('code' in vals or 'name' in vals):
            hashed_aml_domain = [
                ('account_id', 'in', self.ids),
                ('move_id.inalterable_hash', '!=', False),
            ]
            if self.env['account.move.line'].search_count(hashed_aml_domain, limit=1):
                raise UserError(_("You can not change the code/name of an account if it contains hashed entries."))
        super().write(vals)
