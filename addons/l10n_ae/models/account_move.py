from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.company_id.country_code == 'AE':
            return 'l10n_ae.l10n_ae_report_invoice_document'
        return super()._get_name_invoice_report()

    def _l10n_ae_is_simplified(self):
        """
            Returns True if the customer is an individual, i.e: The invoice is B2C
        :return:
        """
        self.ensure_one()
        return self.partner_id.company_type == 'person'
