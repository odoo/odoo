# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import account
from odoo import models


class AccountMove(models.Model, account.AccountMove):

    def _get_name_invoice_report(self):
        if self.company_id.account_fiscal_country_id.code == 'AU':
            return 'l10n_au.report_invoice_document'
        return super()._get_name_invoice_report()
