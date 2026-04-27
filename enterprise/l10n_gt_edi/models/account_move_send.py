from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_gt_edi_applicable(self, move):
        return all([
            move.country_code == 'GT',
            not move.l10n_gt_edi_state,
            move.l10n_gt_edi_doc_type,
        ])

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'gt_edi': {'label': _("Send to SAT"), 'is_applicable': self._is_gt_edi_applicable}})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)

        gt_invoices = moves.filtered(lambda m: 'gt_edi' in moves_data[m]['extra_edis'])

        if len(gt_invoices) == 1 and (gt_alerts := gt_invoices._l10n_gt_edi_get_alerts()):
            alerts = gt_alerts
        elif len(gt_invoices) >= 2 and (gt_bad_invoices := gt_invoices.filtered(lambda m: m._l10n_gt_edi_get_alerts())):
            alerts['l10n_gt_edi_warning_not_ready_invoice'] = {
                'message': _("The following invoice(s) are not ready to be sent to the SAT:%s",
                             ''.join(f"\n- {move.display_name}" for move in gt_bad_invoices)),
                'action_text': _("View Invoice(s)"),
                'action': gt_bad_invoices._get_records_action(name=_("Check Invoice(s)")),
            }

        return alerts

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.l10n_gt_edi_attachment_id

    @api.model
    def _get_placeholder_mail_attachments_data(self, move, invoice_edi_format=None, extra_edis=None):
        # EXTENDS 'account'
        res = super()._get_placeholder_mail_attachments_data(move, invoice_edi_format=invoice_edi_format, extra_edis=extra_edis)

        if not move.l10n_gt_edi_attachment_id and 'gt_edi' in extra_edis:
            attachment_name = move._l10n_gt_edi_get_sat_xml_name()
            res.append(
                {
                    'id': f'placeholder_{attachment_name}',
                    'name': attachment_name,
                    'mimetype': 'application/xml',
                    'placeholder': True,
                }
            )
        return res

    # -------------------------------------------------------------------------
    # SENDING METHOD
    # -------------------------------------------------------------------------

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if 'gt_edi' in invoice_data['extra_edis']:
                invoice._l10n_gt_edi_try_send()

                gt_document = invoice.l10n_gt_edi_document_ids.sorted()[:1]

                if gt_document.state == 'invoice_sending_failed':
                    invoice_data['error'] = {
                        'error_title': _("Error when sending the XML to the SAT"),
                        'errors': gt_document.message.split('\n')[1:],
                    }
