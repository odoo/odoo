# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class L10nBrEDIInvoiceUpdate(models.TransientModel):
    _name = "l10n_br_edi.invoice.update"
    _description = "Implements both correcting and cancelling an invoice."

    move_id = fields.Many2one("account.move", string="Move To Cancel", required=True, help="The move to be cancelled.")
    reason = fields.Char("Reason", required=True, help="The justification for altering this move.")
    mode = fields.Selection(
        [("cancel", "Cancel"), ("correct", "Correct")],
        string="Mode",
        required=True,
        readonly=True,
        help="Technical field to determine whether the move is cancelled or corrected.",
    )
    send_email = fields.Boolean(
        "Email",
        default=True,
        help="When checked an email will be sent informing the customer of the changes and the new EDI documents.",
    )

    def _create_xml_attachment(self, response):
        return self.env["ir.attachment"].create(
            {
                "name": f"{self.move_id.name}_edi_{'cancel' if self.mode == 'cancel' else 'correction'}.xml",
                "datas": response["xml"]["base64"],
            }
        )

    def _log_update(self, success_message, attachments):
        move = self.move_id
        if self.send_email:
            move.with_context(force_send=True, no_new_invoice=True, wizard_mode=self.mode).message_post_with_source(
                "l10n_br_edi.mail_template_move_update",
                attachment_ids=attachments.ids,
            )
        else:
            move.with_context(no_new_invoice=True).message_post(
                body=success_message,
                attachment_ids=attachments.ids,
            )

    def _finalize_update(self, iap_args):
        move = self.move_id
        if self.mode == "cancel":
            move.l10n_br_last_edi_status = "cancelled"
            move.button_cancel()
        else:
            move.l10n_br_edi_last_correction_number = iap_args["seq"]

    def action_submit(self):
        attachments = self.env["ir.attachment"]
        move = self.move_id
        iap_args = {
            "key": move.l10n_br_access_key,
            "message": self.reason,
        }
        if self.mode == "cancel":
            success_message = _("E-invoice cancelled successfully.")
            response = move._l10n_br_iap_cancel_invoice_goods(iap_args)
            if error := move._l10n_br_get_error_from_response(response):
                raise ValidationError(error)
        else:
            success_message = _('E-invoice corrected successfully for reason "%s".', self.reason)
            iap_args["seq"] = move.l10n_br_edi_last_correction_number + 1
            response = move._l10n_br_iap_correct_invoice_goods(iap_args)
            if not response["xml"]["base64"]:
                raise ValidationError(response["status"]["desc"])
            attachments |= self.env["ir.attachment"].create(
                {
                    "name": f"{move.name}_edi_correction.pdf",
                    "datas": response["pdf"]["base64"],
                }
            )

        attachments |= self._create_xml_attachment(response)
        self._log_update(success_message, attachments)
        self._finalize_update(iap_args)
