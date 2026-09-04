from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_name_invoice_report(self):
        # EXTENDS account
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code == 'MU':
            return 'l10n_mu_account.report_invoice_document'
        return super()._get_name_invoice_report()

    def _get_document_title(self, proforma=False, is_debit_note=False):
        self.ensure_one()

        if (
            self.company_id.account_fiscal_country_id.code != 'MU'
            or is_debit_note
            or self.move_type != 'out_invoice'
        ):
            return super()._get_document_title(proforma=proforma, is_debit_note=is_debit_note)

        doc_name = self.env._("VAT Invoice")

        if proforma:
            doc_name = self.env._("Proforma %(doc_name)s", doc_name=doc_name)

        if self.state == 'draft':
            doc_name = self.env._("Draft %(doc_name)s", doc_name=doc_name)
        elif self.state == 'cancel':
            doc_name = self.env._("Cancelled %(doc_name)s", doc_name=doc_name)

        return doc_name
