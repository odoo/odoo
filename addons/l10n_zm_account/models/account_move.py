# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons import account


class AccountMove(account.AccountMove):

    def _get_name_invoice_report(self):
        if self.company_id.account_fiscal_country_id.code == 'ZM':
            return 'l10n_zm_account.report_invoice_document'
        return super()._get_name_invoice_report()
