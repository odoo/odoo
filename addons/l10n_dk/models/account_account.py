from collections import defaultdict

from odoo import api, models, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = ['account.account']
    
    @api.ondelete(at_uninstall=False)
    def _unlink_bank_cash_accounts(self):
        nb_account_to_delete_per_company = defaultdict(self.env['account.account'].browse)
        for account in self:
            for company in account.company_ids:
                if company.country_code == 'DK':
                    nb_account_to_delete_per_company[company] |= account

        if not nb_account_to_delete_per_company:
            return

        grouped_counts = self.read_group(
            domain=[('company_ids.account_fiscal_country_id.code', '=', 'DK'), ('account_type', '=', 'asset_cash')],
            fields=['company_ids', 'id:count'],
            groupby=['company_ids'],
        )
        nb_account_per_company = {self.env['res.company'].browse(entry['company_ids'][0]): entry['company_ids_count'] for entry in grouped_counts}

        for company_id, count in nb_account_per_company.items():
            nb_to_delete = sum(1 for account in nb_account_to_delete_per_company.get(company_id) if account.account_type == 'asset_cash')
            if count - nb_to_delete < 1:
                raise UserError(_("You must keep at least one bank and cash account for %(company)s!", company=company_id.name))
