from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    @api.model
    def _is_uy_edi_applicable(self, move):
        return move.l10n_uy_edi_is_needed

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'uy_cfe': {'label': _("Create CFE"), 'is_applicable': self._is_uy_edi_applicable}})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if non_eligible_uy_moves := moves.filtered(lambda m: 'uy_cfe' in moves_data[m]['extra_edis'] and not m.l10n_uy_edi_is_needed):
            alerts['l10n_uy_edi_non_eligible'] = {
                'message': _(
                    "Uruguayan e-invoicing was enabled but the following invoices cannot be e-invoiced:\n%s\n"
                    "If this is not intended, please check if an UCFE Uruware is properly set or if the invoice"
                    " isn't already e-invoiced.\n", "".join(f"- {move.display_name}" for move in non_eligible_uy_moves)
                ),
                'action_text': _("View Invoice(s)"),
                'action': non_eligible_uy_moves._get_records_action(name=_("Check Invoice(s)")),
            }
        return alerts

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS "account"
        return super()._get_invoice_extra_attachments(move) + move.l10n_uy_edi_xml_attachment_id

    def _get_placeholder_mail_attachments_data(self, move, invoice_edi_format=None, extra_edis=None):
        # EXTENDS "account"
        res = super()._get_placeholder_mail_attachments_data(move, invoice_edi_format=invoice_edi_format, extra_edis=extra_edis)
        if 'uy_cfe' in extra_edis:
            attachment_name = move.l10n_uy_edi_document_id._get_xml_attachment_name()
            res.append({
                "id": f"placeholder_{attachment_name}",
                "name": attachment_name,
                "mimetype": "application/xml",
                "placeholder": True,
            })
        return res

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _hook_if_success(self, moves_data):
        # EXTENDS "account"
        for move, move_data in moves_data.items():
            if 'email' in move_data['sending_methods'] and move.l10n_uy_edi_cfe_state in ("received", "accepted"):
                mail_template = moves_data[move]["mail_template"]
                mail_lang = moves_data[move]["mail_lang"]
                moves_data[move].update({
                    "mail_body": self._get_default_mail_body(move, mail_template, mail_lang),
                    "mail_subject": self._get_default_mail_subject(move, mail_template, mail_lang),
                })
        return super()._hook_if_success(moves_data)

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS "account"
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        if 'uy_cfe' in invoice_data['extra_edis']:
            if errors := invoice._l10n_uy_edi_check_move():
                invoice_data["error"] = {
                    "error_title": _("Errors occurred while creating the EDI document (CFE):"),
                    "errors": errors,
                }

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS "account"
        super()._call_web_service_before_invoice_pdf_render(invoices_data)
        for invoice, invoice_data in invoices_data.items():
            if 'uy_cfe' in invoice_data['extra_edis']:
                invoice._l10n_uy_edi_send()
                if invoice.l10n_uy_edi_error:
                    invoice_data["error"] = {
                        "error_title": _("Errors when submitting the e-invoice:"),
                        "errors": [invoice.l10n_uy_edi_error],
                    }

                if self._can_commit():
                    self._cr.commit()
