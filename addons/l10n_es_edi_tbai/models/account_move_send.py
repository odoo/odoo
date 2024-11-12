from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_tbai_applicable(self, move):
        return move.l10n_es_tbai_is_required and move.l10n_es_tbai_state == 'to_send'

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'es_tbai': {'label': _("TicketBAI"), 'is_applicable': self._is_tbai_applicable, 'help': _('Send the e-invoice to the Basque Government.')}})
        return res

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.l10n_es_tbai_post_document_id.xml_attachment_id

    def _get_placeholder_mail_attachments_data(self, move, extra_edis=None):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move, extra_edis=extra_edis)

        if (
            not move.l10n_es_tbai_post_document_id.xml_attachment_id
            and 'es_tbai' in extra_edis
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

            if 'es_tbai' in invoice_data['extra_edis']:
                error = invoice._l10n_es_tbai_post()

                if error:
                    invoice_data['error'] = {
                        'error_title': _("Error when sending the invoice to TicketBAI:"),
                        'errors': [error],
                    }

                if self._can_commit():
                    self._cr.commit()
