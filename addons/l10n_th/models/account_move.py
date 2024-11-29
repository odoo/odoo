from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code == 'TH':
            return 'l10n_th.report_invoice_document'
        return super()._get_name_invoice_report()
