from odoo import api, models
from odoo.tools import html2plaintext


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_l10n_pk_edi_applicable(self, move):
        """Check if the PK E-Invoice applies to the given move."""
        return move._l10n_pk_edi_default_enable() and not move.company_id.l10n_pk_edi_test_environment

    @api.model
    def _is_l10n_pk_edi_test_applicable(self, move):
        """Check if the PK E-Invoice Testing applies to the given move."""
        return move._l10n_pk_edi_default_enable() and move.company_id.l10n_pk_edi_test_environment

    def _get_all_extra_edis(self):
        """Extend the EDI providers with the PK E-Invoice option."""
        res = super()._get_all_extra_edis()
        res.update({
        "l10n_pk_edi": {
            'label': self.env._("To FBR"),
            'is_applicable': self._is_l10n_pk_edi_applicable,
        },
        "l10n_pk_edi_test": {
            'label': self.env._("To FBR (Test)"),
            'is_applicable': self._is_l10n_pk_edi_test_applicable,
        }})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_alerts(self, moves, moves_data):
        alerts = super()._get_alerts(moves, moves_data)
        pk_moves = moves.filtered(lambda m: not {'l10n_pk_edi', 'l10n_pk_edi_test'}.isdisjoint(moves_data[m]['extra_edis']))
        alerts.update(pk_moves.mapped("company_id")._l10n_pk_edi_export_check())
        alerts.update(pk_moves.partner_id._l10n_pk_edi_export_check())
        alerts.update(pk_moves.mapped("invoice_line_ids.product_id")._l10n_pk_edi_export_check())
        alerts.update(pk_moves.mapped("invoice_line_ids.product_id.uom_id")._l10n_pk_edi_export_check())
        return alerts

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) | move.l10n_pk_edi_attachment_id

    @api.model
    def _get_placeholder_mail_attachments_data(self, move, invoice_edi_format=None, extra_edis=None, pdf_report=None):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(
            move,
            invoice_edi_format=invoice_edi_format,
            extra_edis=extra_edis,
            pdf_report=pdf_report,
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
            if {'l10n_pk_edi', 'l10n_pk_edi_test'}.isdisjoint(invoice_data.get('extra_edis', [])):
                continue
            response = invoice._l10n_pk_edi_send()
            if not response or not response.get('error'):
                continue
            invoice_data['error'] = {
                'error_title': self.env._("Error while sending e-invoice to government:"),
                'errors': [
                    line.lstrip('- ').strip()
                    for line in html2plaintext(invoice.l10n_pk_edi_status_message).split('\n')
                    if line.strip()
                ],
            }
            if self._can_commit():
                self._cr.commit()
