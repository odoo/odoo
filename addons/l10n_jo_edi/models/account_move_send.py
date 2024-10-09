from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    @api.model
    def _l10n_jo_is_edi_applicable(self, move):
        return move.l10n_jo_edi_is_needed and move.l10n_jo_edi_state != 'sent'

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'jo_edi': {'label': _("JoFotara (Jordan EDI)"), 'is_applicable': self._l10n_jo_is_edi_applicable}})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if non_eligible_jo_moves := moves.filtered(lambda m: 'jo_edi' in moves_data[m]['extra_edis'] and not self._l10n_jo_is_edi_applicable(m)):
            alerts['l10n_jo_edi_non_eligible_moves'] = {
                'message': _(
                    "JoFotara e-invoicing was enabled but the following invoices cannot be e-invoiced:\n%(moves)s\n",
                    moves="\n".join(f"- {move.display_name}" for move in non_eligible_jo_moves),
                ),
                'action_text': _("View Invoice(s)"),
                'action': non_eligible_jo_moves._get_records_action(name=_("Check Invoice(s)")),
            }
        return alerts

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.l10n_jo_edi_xml_attachment_id

    def _get_placeholder_mail_attachments_data(self, move, extra_edis=None):
        # EXTENDS 'account'
        res = super()._get_placeholder_mail_attachments_data(move, extra_edis=extra_edis)

        if not move.l10n_jo_edi_xml_attachment_id and 'jo_edi' in extra_edis:
            attachment_name = move._l10n_jo_edi_get_xml_attachment_name()
            res.append(
                {
                    "id": f"placeholder_{attachment_name}",
                    "name": attachment_name,
                    "mimetype": "application/xml",
                    "placeholder": True,
                }
            )
        return res

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if 'jo_edi' in invoice_data['extra_edis']:
                if error_message := invoice.with_company(invoice.company_id)._l10n_jo_edi_send():
                    invoice_data["error"] = {
                        "error_title": _("Errors when submitting the JoFotara e-invoice:"),
                        "errors": [error_message],
                    }

                if self._can_commit():
                    self._cr.commit()
