from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_mail_template(self):
        if all(move.move_type == 'in_invoice' and move.journal_id.is_self_billing for move in self):
            return self.env.ref('account_peppol_selfbilling.email_template_edi_self_billing_invoice')
        elif all(move.move_type == 'in_refund' and move.journal_id.is_self_billing for move in self):
            return self.env.ref('account_peppol_selfbilling.email_template_edi_self_billing_credit_note')
        return super()._get_mail_template()

    def _compute_display_send_button(self):
        # EXTENDS 'account'
        super()._compute_display_send_button()
        for move in self:
            if move._is_exportable_as_self_invoice():
                move.display_send_button = True

    def _is_exportable_as_self_invoice(self):
        return (
            self.state == 'posted'
            and self.is_purchase_document()
            and (invoice_edi_format := self.commercial_partner_id._get_peppol_edi_format())
            and (edi_builder := self.partner_id._get_edi_builder(invoice_edi_format)) is not None
            and edi_builder._can_export_selfbilling()
            and self.journal_id.is_self_billing
        )
