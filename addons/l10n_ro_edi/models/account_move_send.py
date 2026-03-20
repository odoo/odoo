from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_ro_edi_applicable(self, move):
        return all([
            move._need_ubl_cii_xml('ciusro') or move.ubl_cii_xml_id,
            move.country_code == 'RO',
            not move.l10n_ro_edi_state,
        ])

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'ro_edi': {'label': _("Send E-Factura to SPV"), 'is_applicable': self._is_ro_edi_applicable}})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if waiting_moves := moves.filtered(lambda m: m.l10n_ro_edi_state in ['invoice_not_indexed', 'invoice_sent']):
            alerts['l10n_ro_edi_warning_waiting_moves'] = {
                'message': _(
                    "The following invoice(s) are waiting for answer from the Romanian SPV: %s."
                    "We won't send them again.",
                    ', '.join(waiting_moves.mapped('name'))
                ),
                'action_text': _("View Invoice(s)"),
                'action': waiting_moves._get_records_action(name=_("Check Invoice(s)")),
            }
        return alerts

    # -------------------------------------------------------------------------
    # SENDING METHOD
    # -------------------------------------------------------------------------

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        if 'ro_edi' in invoice_data['extra_edis']:
            invoice_data['invoice_edi_format'] = 'ciusro'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if 'ro_edi' in invoice_data['extra_edis']:

                if invoice.l10n_ro_edi_document_ids:
                    # If a document is on the invoice, we shouldn't send it again
                    invoice_data['error'] = {
                        'error_title': _("The CIUS-RO E-Factura has already been sent"),
                    }
                    continue

                if invoice_data.get('ubl_cii_xml_attachment_values'):
                    xml_data = invoice_data['ubl_cii_xml_attachment_values']['raw']
                elif invoice.ubl_cii_xml_id:
                    xml_data = invoice.ubl_cii_xml_id.raw
                else:
                    invoice_data['error'] = {
                        'error_title': _("The CIUS-RO E-Factura could not be found"),
                    }
                    continue

                if errors := invoice._l10n_ro_edi_send_invoice(xml_data):
                    invoice_data['error'] = {
                        'error_title': _("Error when sending CIUS-RO E-Factura to the SPV"),
                        'errors': errors,
                    }
