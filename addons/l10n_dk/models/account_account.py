from odoo import api, models, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = ['account.account']
    
    @api.ondelete(at_uninstall=False)
    def _unlink_bank_cash_accounts(self):
        if self.env.company.country_code != 'DK':
            return

        nb_bank_cash_account = self.search_count([
            ('company_id', '=', self.env.company.id),
            ('account_type', '=', 'asset_cash'),
        ])
        for account in self:
            if account.account_type == 'asset_cash' and nb_bank_cash_account == 1:
                raise UserError(_("You must keep at least one bank and cash account!"))
            nb_bank_cash_account -= 1
