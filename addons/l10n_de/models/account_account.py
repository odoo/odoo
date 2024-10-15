from odoo import models, _
from odoo.exceptions import UserError
from odoo.addons import account


class AccountAccount(account.AccountAccount):

    def write(self, vals):
        if (
            'code' in vals
            and 'DE' in self.company_ids.account_fiscal_country_id.mapped('code')
            and any(a.code != vals['code'] for a in self)
        ):
            if self.env['account.move.line'].search_count([('account_id', 'in', self.ids)], limit=1):
                raise UserError(_("You can not change the code of an account."))
        return super().write(vals)
