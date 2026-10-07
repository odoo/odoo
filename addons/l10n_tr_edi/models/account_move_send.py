from io import BytesIO

from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_tr_edi_applicable(self, move):
        return (
            move.l10n_tr_edi_send_status in {'not_sent', 'draft_sent'}
            and move.is_invoice(include_receipts=True)
            and move.country_code == 'TR'
            and move.company_id.l10n_tr_edi_provider
        )

    @api.model
    def _l10n_tr_edi_get_extra_edi_label(self):
        """Return the label of the Turkish e-Document checkbox of the sending wizard.

        Provider modules override this to name the provider of the current company.
        """
        return self.env._("Send to GİB")

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'tr_edi': {'label': self._l10n_tr_edi_get_extra_edi_label(), 'is_applicable': self._is_tr_edi_applicable}})
        return res

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if 'tr_edi' in invoice_data['extra_edis']:
                if attachment_values := invoice_data.get('ubl_cii_xml_attachment_values'):
                    xml_file = BytesIO(attachment_values.get('raw'))
                    xml_file.name = attachment_values.get('name')
                else:
                    xml_file = BytesIO(invoice.ubl_cii_xml_id.raw)
                    xml_file.name = invoice.ubl_cii_xml_id.name

                if errors := invoice._l10n_tr_edi_send(xml_file):
                    invoice_data['error'] = {
                        'error_title': self.env._("Error when sending the e-Document"),
                        'errors': errors,
                    }

                if self._can_commit():
                    self.env.cr.commit()

    @api.model
    def _postprocess_invoice_ubl_xml(self, invoice, invoice_data):
        # EXTENDS 'account_edi_ubl_cii'
        # The UBL-TR XML is registered at the GİB as it was sent, before the PDF exists: keep it unchanged.
        if invoice_data['invoice_edi_format'] == 'ubl_tr':
            return

        return super()._postprocess_invoice_ubl_xml(invoice, invoice_data)

    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account_edi_ubl_cii'
        super()._link_invoice_documents(invoices_data)
        for invoice in invoices_data:
            if invoice.ubl_cii_xml_id and (document := invoice.l10n_tr_edi_document_ids.filtered(
                lambda d: d.document_type != 'commercial_response',
            )[:1]):
                document.attachment_id = invoice.ubl_cii_xml_id
            # The move needs to be put as sent only once its e-Document is sent.
            if invoice.company_id.country_code == 'TR' and invoice.company_id.l10n_tr_edi_provider:
                invoice.is_move_sent = invoice.l10n_tr_edi_send_status == 'sent'

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if tr_edi_moves := moves.filtered(lambda m: 'tr_edi' in moves_data[m]['extra_edis']):
            alerts.update(tr_edi_moves._l10n_tr_edi_get_alerts())
        if moves.filtered(
            lambda m: (
                m.country_code == 'TR'
                and m.is_invoice(include_receipts=True)
                and m.l10n_tr_edi_send_status == 'not_sent'
                and not m.company_id.l10n_tr_edi_provider
            ),
        ):
            # Without a provider the GİB option is not offered: say why, the invoice is only e-mailed.
            alerts['l10n_tr_edi_no_provider'] = {
                'message': self.env._("No e-Document provider is set, so these invoices are not sent to the GİB."),
                'level': 'info',
                'action_text': self.env._("Set a provider"),
                'action': self.env['ir.actions.act_window']._for_xml_id('account.action_account_config'),
            }
        return alerts

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------
