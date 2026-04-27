# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    @api.model
    def _is_br_edi_applicable(self, move):
        return move.l10n_br_edi_is_needed

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'br_edi': {'label': _("e-invoice (Brazil)"), 'is_applicable': self._is_br_edi_applicable}})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if non_eligible_br_moves := moves.filtered(lambda m: 'br_edi' in moves_data[m]['extra_edis'] and not self._is_br_edi_applicable(m)):
            alerts['l10n_br_edi_non_eligible_moves'] = {
                'message': _(
                    "Brazilian e-invoicing was enabled but the following invoices cannot be e-invoiced:\n%s\n"
                    "If this is not intended, please check if an Avatax fiscal position is used on those invoices and if the invoice isn't already e-invoiced.",
                    "\n".join(f"- {move.display_name}" for move in non_eligible_br_moves),
                ),
                'action_text': _("View Invoice(s)"),
                'action': non_eligible_br_moves._get_records_action(name=_("Check Invoice(s)")),
            }
        return alerts

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.l10n_br_edi_xml_attachment_id

    def _get_placeholder_mail_attachments_data(self, move, invoice_edi_format=None, extra_edis=None):
        # EXTENDS 'account'
        res = super()._get_placeholder_mail_attachments_data(move, invoice_edi_format=invoice_edi_format, extra_edis=extra_edis)

        if not move.l10n_br_edi_xml_attachment_id and 'br_edi' in extra_edis:
            attachment_name = move._l10n_br_edi_get_xml_attachment_name()
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
            # Not all invoices may need EDI.
            if 'br_edi' in invoice_data['extra_edis']:
                if errors := invoice.with_company(invoice.company_id)._l10n_br_edi_send():
                    invoice.l10n_br_edi_error = "\n".join(errors)
                    invoice_data["error"] = {
                        "error_title": _("Errors when submitting the e-invoice:"),
                        "errors": errors,
                    }
                else:
                    invoice.l10n_br_edi_error = False

                if self._can_commit():
                    self._cr.commit()
