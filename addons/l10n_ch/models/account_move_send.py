from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_alerts(self, moves, moves_data):
        alerts = super()._get_alerts(moves, moves_data)

        l10n_ch_partners_without_street = moves.filtered(lambda move: (
            move.l10n_ch_is_qr_valid
            and not move.partner_id.street
            and not move.partner_id.street2
        )).partner_id
        if l10n_ch_partners_without_street:
            alerts['l10n_ch_partners_without_street'] = {
                'level': 'warning',
                'message': _("You might want to specify an address on the following partner(s)."),
                'action_text': _("View Partner(s)"),
                'action': l10n_ch_partners_without_street._get_records_action(),
            }

        return alerts

    @api.model
    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS account
        # Prevents the QR Code Errors from blocking the execution of the cron.
        # The invoices with errors will be skipped and the error message displayed
        # in the chatter
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        if (bool(self.env.context.get('ir_cron_progress_id'))
            and invoice.l10n_ch_is_qr_valid
            and self.env['ir.actions.report']._is_invoice_report(invoice_data.get('pdf_report'))
            and (qr_code_errors := invoice.partner_bank_id._check_for_qr_code_errors(
                qr_method='ch_qr',
                amount=invoice.amount_residual,
                currency=invoice.currency_id,
                debtor_partner=invoice.partner_id,
                free_communication=invoice.payment_reference or invoice.name,
                structured_communication=invoice.payment_reference))):
            invoice_data['error'] = {
                'error_title': _('Errors occured during the generation of the "Swiss QR bill" QR-code.'),
                'errors': [qr_code_errors],
            }
