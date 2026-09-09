# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_name_invoice_report(self):
        if self.company_id.account_fiscal_country_id.code == 'ZM':
            return 'l10n_zm_account.report_invoice_document'
        return super()._get_name_invoice_report()

    def _get_document_title(self, proforma=False, is_debit_note=False):
        self.ensure_one()

        if (
            self.company_id.account_fiscal_country_id.code != 'ZM'
            or is_debit_note
            or self.move_type != 'out_invoice'
        ):
            return super()._get_document_title(proforma=proforma, is_debit_note=is_debit_note)

        doc_name = self.env._("Tax Invoice")

        if self.state == 'posted':
            doc_name = self.env._("Fiscal %(doc_name)s", doc_name=doc_name)

        if proforma:
            doc_name = self.env._("Proforma %(doc_name)s", doc_name=doc_name)

        if self.state == 'draft':
            doc_name = self.env._("Draft %(doc_name)s", doc_name=doc_name)
        elif self.state == 'cancel':
            doc_name = self.env._("Cancelled %(doc_name)s", doc_name=doc_name)

        return doc_name
