from odoo import models, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    def write(self, vals):
        if (
            'code' in vals
            and self.env.company.account_fiscal_country_id.code == 'DE'
            and any(
                self.env.company in a.company_ids and a.code != vals['code']
                for a in self
            )
        ):
            if self.env['account.move.line'].search_count([('account_id', 'in', self.ids)], limit=1):
                raise UserError(_("You can not change the code of an account."))
        return super().write(vals)
