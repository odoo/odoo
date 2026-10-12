from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_l10n_pk_edi_applicable(self, move):
        """Check if the PK E-Invoice applies to the given move."""
        return move._l10n_pk_edi_default_enable() and not move.company_id._l10n_pk_edi_is_test_mode()

    @api.model
    def _is_l10n_pk_edi_test_applicable(self, move):
        """Check if the PK E-Invoice Testing applies to the given move."""
        return move._l10n_pk_edi_default_enable() and move.company_id._l10n_pk_edi_is_test_mode()

    def _get_all_extra_edis(self):
        """Extend the EDI providers with the PK E-Invoice option."""
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({
            "l10n_pk_edi": {
                'label': self.env._("To FBR"),
                'is_applicable': self._is_l10n_pk_edi_applicable,
            },
            "l10n_pk_edi_test": {
                'label': self.env._("To FBR (Test)"),
                'is_applicable': self._is_l10n_pk_edi_test_applicable,
            },
        })
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        pk_moves = moves.filtered(lambda m: not {'l10n_pk_edi', 'l10n_pk_edi_test'}.isdisjoint(moves_data[m]['extra_edis']))
        alerts.update(pk_moves._l10n_pk_edi_export_check())
        alerts.update(pk_moves.company_id._l10n_pk_edi_export_check())
        alerts.update(pk_moves.partner_id._l10n_pk_edi_export_check())
        alerts.update(pk_moves.invoice_line_ids.product_id._l10n_pk_edi_export_check())
        alerts.update(pk_moves.invoice_line_ids.product_id.uom_id._l10n_pk_edi_export_check())
        return alerts

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
                    error
                    for line in response['error']['message'].split('\n')
                    if (error := line.strip())
                ],
            }
            if self._can_commit():
                self._cr.commit()
