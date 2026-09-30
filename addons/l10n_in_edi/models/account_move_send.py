from odoo import api, fields, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_in_edi_applicable(self, move):
        return (
            move._l10n_in_check_einvoice_eligible()
            and move.state == 'posted'
            and move.l10n_in_edi_status != 'sent'
        )

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({
            'in_edi_send': {
                'label': self.env._("E-invoicing"),
                'is_applicable': self._is_in_edi_applicable,
                'help': self.env._(
                    "Send the e-invoice json to the Indian Invoice Registration Portal (IRP)."
                )
            }
        })
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if in_moves := moves.filtered(lambda m: 'in_edi_send' in moves_data[m]['extra_edis']):
            if in_alerts := in_moves._l10n_in_check_einvoice_validation():
                alerts.update(in_alerts)
        return alerts

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, invoice):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(invoice) + invoice.l10n_in_edi_attachment_id

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)
        for invoice, invoice_data in invoices_data.items():
            if 'in_edi_send' in invoice_data['extra_edis']:
                if error := invoice._l10n_in_edi_send_invoice():
                    invoice_data['error'] = {
                        'error_title': self.env._(
                            "Error when sending the invoice to government:"
                        ),
                        'errors': error['messages'],
                        'retry': error.get('is_warning'),
                    }
                elif invoice.invoice_pdf_report_id:
                    invoice.write({'invoice_pdf_report_file': False})
                if self._can_commit():
                    self.env.cr.commit()
