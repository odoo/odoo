from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_tbai_applicable(self, move):
        return move.l10n_es_tbai_is_required and move.l10n_es_tbai_state == 'to_send'

    def _get_default_extra_edi_checkboxes(self, move):
        # EXTENDS 'account'
        extra_edi = super()._get_default_extra_edi_checkboxes(move)
        if self._is_tbai_applicable(move):
            extra_edi['es_tbai'] = {'checked': True, 'readonly': False, 'label': _('TicketBAI'), 'help': _('Send the e-invoice to the Basque Government.')}
        return extra_edi

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.l10n_es_tbai_post_document_id.xml_attachment_id

    def _get_placeholder_mail_attachments_data(self, move, invoice_edi_format=None, extra_edi=None):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move, invoice_edi_format=invoice_edi_format, extra_edi=extra_edi)

        if (
            not move.l10n_es_tbai_post_document_id.xml_attachment_id
            and 'es_tbai' in extra_edi
        ):
            filename = move._l10n_es_tbai_get_attachment_name()
            results.append({
                'id': f'placeholder_{filename}',
                'name': filename,
                'mimetype': 'application/xml',
                'placeholder': True,
            })

        return results

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():

            if 'es_tbai' in invoice_data['extra_edi']:
                error = invoice._l10n_es_tbai_post()

                if error:
                    invoice_data['error'] = {
                        'error_title': _("Error when sending the invoice to TicketBAI:"),
                        'errors': [error],
                    }

                if self._can_commit():
                    self._cr.commit()
