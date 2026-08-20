from collections import defaultdict

from odoo import api, models
from odoo.exceptions import UserError


class JoFotaraRejection(UserError):
    """ A rejection carrying the computed XML.

    The client keys l10n_jo_edi's error dialog on this class' dotted path, so it must stay
    importable from here; see static/src/jo_edi_error_dialog/jo_edi_error_dialog.js.
    """


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _l10n_jo_is_edi_applicable(self, move):
        return move.l10n_jo_edi_is_needed and move.l10n_jo_edi_state not in ['sent', 'demo']

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        label = self.env._("To JoFotara (Demo)") if self.env.company.l10n_jo_edi_demo_mode else self.env._("To JoFotara")
        res.update({'jo_edi': {'label': label, 'is_applicable': self._l10n_jo_is_edi_applicable}})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        invalid_moves = defaultdict(lambda: self.env['account.move'])
        for move in moves.filtered(lambda m: 'jo_edi' in moves_data[m]['extra_edis'] and self._l10n_jo_is_edi_applicable(m)):
            for message in move._l10n_jo_edi_get_validation_errors():
                invalid_moves[message] |= move
        # one alert per defect, listing the affected invoices behind the action, instead of one alert per invoice
        for index, (message, error_moves) in enumerate(invalid_moves.items()):
            alerts[f'l10n_jo_edi_validation_error_{index}'] = {
                'level': 'danger',
                'message': message,
                'action_text': self.env._("View Invoices"),
                'action': error_moves._get_records_action(),
            }
        if non_eligible_jo_moves := moves.filtered(lambda m: 'jo_edi' in moves_data[m]['extra_edis'] and not self._l10n_jo_is_edi_applicable(m)):
            alerts['l10n_jo_edi_non_eligible_moves'] = {
                'message': self.env._("JoFotara e-invoicing was enabled but some of the selected invoices cannot be e-invoiced."),
                'action_text': self.env._("View Invoices"),
                'action': non_eligible_jo_moves._get_records_action(),
            }
        return alerts

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.l10n_jo_edi_xml_attachment_id

    def _get_placeholder_mail_attachments_data(self, move, invoice_edi_format=None, extra_edis=None, pdf_report=None):
        # EXTENDS 'account'
        res = super()._get_placeholder_mail_attachments_data(move, invoice_edi_format=invoice_edi_format, extra_edis=extra_edis, pdf_report=pdf_report)

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

        error_title = self.env._("Error: Invoice was not sent to JoFotara")
        for invoice, invoice_data in invoices_data.items():
            if 'jo_edi' in invoice_data['extra_edis']:
                invoice = invoice.with_company(invoice.company_id)
                if validation_errors := invoice._l10n_jo_edi_get_validation_errors():
                    # pre-validation errors are shown by the wizard alert, they must not open the XML pop-up
                    invoice.l10n_jo_edi_error = "\n".join(validation_errors)
                    invoice_data["error"] = {
                        "error_title": error_title,
                        "errors": validation_errors,
                    }
                elif error_message := invoice._l10n_jo_edi_send():
                    invoice_data["error"] = {
                        "error_title": error_title,
                        "errors": [error_message],
                        "l10n_jo_edi_xml_url": invoice._l10n_jo_edi_get_computed_xml_url(),
                    }

                if self._can_commit():
                    # keep the JoFotara answer when the interactive error dialog rolls the request back
                    self.env.cr.commit()

    @api.model
    def _hook_if_errors(self, moves_data, allow_raising=True):
        # EXTENDS 'account'
        if allow_raising and len(moves_data) == 1:
            error = next(iter(moves_data.values()))['error']
            if xml_url := error.get('l10n_jo_edi_xml_url'):
                rejection = JoFotaraRejection(self._format_error_text(error))
                # forwarded as-is by serialize_exception, and read by the dialog
                rejection.context = {'l10n_jo_edi': {'xml_url': xml_url}}
                raise rejection
        return super()._hook_if_errors(moves_data, allow_raising=allow_raising)
