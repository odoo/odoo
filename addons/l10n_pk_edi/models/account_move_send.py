from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_l10n_pk_edi_applicable(self, move) -> bool:
        """Check if the PK E-Invoice applies to the given move."""

        return move._l10n_pk_edi_default_enable()

    def _get_all_extra_edis(self) -> dict:
        """Extend the EDI providers with the PK E-Invoice option."""

        res = super()._get_all_extra_edis()
        res.update({'l10n_pk_edi': {
            'label': self.env._("PK E-Invoice"),
            'is_applicable': self._is_l10n_pk_edi_applicable,
        }})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        pk_moves = moves.filtered(lambda m: 'l10n_pk_edi' in moves_data[m]['extra_edis'])
        if pk_alerts := pk_moves._l10n_pk_edi_validate():
            alerts.update(**pk_alerts)
        return alerts

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) | move.l10n_pk_edi_attachment_id

    @api.model
    def _get_placeholder_mail_attachments_data(self, move, invoice_edi_format=None, extra_edis=None):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(
            move,
            invoice_edi_format=invoice_edi_format,
            extra_edis=extra_edis,
        )
        if 'l10n_pk_edi' in extra_edis and not move.l10n_pk_edi_attachment_id:
            filename = move._l10n_pk_edi_attachment_name()
            results.append({
                'id': f'placeholder_{filename}',
                'name': filename,
                'mimetype': 'application/json',
                'placeholder': True,
            })
        return results

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)
        for invoice, invoice_data in invoices_data.items():
            if 'l10n_pk_edi' not in invoice_data.get('extra_edis', []):
                continue

            # Call web service for invoice
            response = invoice._l10n_pk_edi_send()
            # Stop the flow if no error is returned
            if not response or not response.get('error'):
                continue

            # Extract error messages from the response
            errors = response['error'].get('message')
            invoice_data['error'] = {
                'error_title': self.env._("Error while sending e-invoice to government:"),
                'errors': errors if isinstance(errors, list) else [errors],
            }

            # Commit to save changes, in case of an issue arises later.
            if self._can_commit():
                self._cr.commit()
