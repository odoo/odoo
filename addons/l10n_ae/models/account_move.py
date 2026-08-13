from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_name_invoice_report(self):
        # EXTENDS account
        self.ensure_one()
        if self.company_id.country_code == 'AE':
            return 'l10n_ae.l10n_ae_report_invoice_document'
        return super()._get_name_invoice_report()

    def _get_document_title(self, proforma=False, is_debit_note=False):
        self.ensure_one()

        if (
            self.company_id.country_code == 'AE'
            and self.state == 'posted'
            and self.move_type in {'out_invoice', 'out_refund'}
            and not is_debit_note
        ):
            if self.move_type == 'out_invoice':
                if self.commercial_partner_id.is_company:
                    return self.env._("Tax Invoice")
                return self.env._("Simplified Tax Invoice")
            else:
                return self.env._("Tax Credit Note")

        return super()._get_document_title(proforma, is_debit_note)
