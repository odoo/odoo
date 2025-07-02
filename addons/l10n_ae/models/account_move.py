from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_name_invoice_report(self):
        # EXTENDS account
        self.ensure_one()
        if self.company_id.country_code == 'AE':
            return 'l10n_ae.l10n_ae_report_invoice_document'
        return super()._get_name_invoice_report()

    def _l10n_gcc_get_invoice_title(self):
        # EXTENDS l10n_gcc_invoice
        self.ensure_one()
        if self.company_id.country_code != 'AE':
            return super()._l10n_gcc_get_invoice_title()

        if self._l10n_ae_is_simplified():
            return self.env._('Simplified Tax Invoice')

        return self.env._('Tax Invoice')

    def _l10n_ae_is_simplified(self):
        """Returns True if the customer is an individual, i.e: The invoice is B2C"""
        self.ensure_one()
        return not self.partner_id.is_company
