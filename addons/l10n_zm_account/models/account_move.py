from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_name_invoice_report(self):
        if self.company_id.account_config_id.account_fiscal_country_id.code == "ZM":
            return "l10n_zm_account.report_invoice_document"
        return super()._get_name_invoice_report()
