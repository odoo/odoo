from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_name_invoice_report(self):
        # EXTENDS account
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code == 'MU':
            return 'l10n_mu_account.report_invoice_document'
        return super()._get_name_invoice_report()
