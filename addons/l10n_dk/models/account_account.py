from odoo import api, models, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = ['account.account']
    
    @api.ondelete(at_uninstall=False)
    def _unlink_bank_cash_accounts(self):
        dk_accounts = self.filtered(lambda acc: acc.company_id.account_fiscal_country_id.code == 'DK')
        if not dk_accounts:
            return

        grouped_counts = self.read_group(
            domain=[('company_id', 'in', dk_accounts.company_id.ids), ('account_type', '=', 'asset_cash')],
            fields=['company_id', 'id:count'],
            groupby=['company_id'],
        )
        nb_account_per_company = {self.env['res.company'].browse(entry['company_id'][0]): entry['company_id_count'] for entry in grouped_counts}
        nb_account_to_delete_per_company = dk_accounts.grouped('company_id')

        for company_id, count in nb_account_per_company.items():
            nb_to_delete = sum(1 for account in nb_account_to_delete_per_company.get(company_id) if account.account_type == 'asset_cash')
            if count - nb_to_delete < 1:
                raise UserError(_("You must keep at least one bank and cash account for %(company)s!", company=company_id.name))
