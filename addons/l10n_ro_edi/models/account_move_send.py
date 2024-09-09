from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_ro_edi_applicable(self, move):
        return all([
            move._need_ubl_cii_xml('ro_edi') or move.ubl_cii_xml_id,
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
        if waiting_moves := moves.filtered(lambda m: m.l10n_ro_edi_state == 'invoice_sent'):
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

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if 'ro_edi' in invoice_data['extra_edis']:
                if invoice_data.get('ubl_cii_xml_attachment_values'):
                    xml_data = invoice_data['ubl_cii_xml_attachment_values']['raw']
                elif invoice.l10n_ro_edi_document_ids:
                    # If a document is on the invoice but the invoice's l10n_ro_edi_state is False,
                    # this means that the previously sent XML are invalid and have to be rebuilt
                    xml_data, build_errors = self.env['account.edi.xml.ubl_ro']._export_invoice(invoice)
                    if build_errors:
                        invoice_data['error'] = {
                            'error_title': _("Error when rebuilding the CIUS-RO E-Factura XML"),
                            'errors': build_errors,
                        }
                        continue
                elif invoice.ubl_cii_xml_id:
                    xml_data = invoice.ubl_cii_xml_id.raw
                else:
                    xml_data = None

                invoice._l10n_ro_edi_send_invoice(xml_data)
                active_document = invoice.l10n_ro_edi_document_ids.sorted()[0]

                if active_document.state == 'invoice_sent_failed':
                    invoice_data['error'] = {
                        'error_title': _("Error when sending CIUS-RO E-Factura to the SPV"),
                        'errors': active_document.message.split('\n'),
                    }
