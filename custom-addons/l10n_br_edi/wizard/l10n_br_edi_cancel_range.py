# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class L10nBrEDICancelRange(models.Model):
    _name = "l10n_br_edi.cancel.range"
    _description = "This allows a user to inform the government a range of sequence numbers won't be used."

    journal_id = fields.Many2one(
        "account.journal",
        "Journal",
        required=True,
        readonly=True,
        help="The journal for which to invalidate the range.",
    )
    document_type_id = fields.Many2one(
        "l10n_latam.document.type",
        "Document Type",
        required=True,
        help="The document type for which to invalidate the range.",
    )
    start_number = fields.Integer("Start number", required=True, help="The first number that should be invalidated.")
    end_number = fields.Integer("End number", required=True, help="The last number that should be invalidated.")
    reason = fields.Char("Reason", required=True, help="The reason for invalidating this range.")

    def action_submit(self):
        AccountMove = self.env["account.move"]
        responses = AccountMove._l10n_br_iap_cancel_range_goods(
            {
                "model": self.document_type_id.doc_code_prefix,
                "serie": self.journal_id.l10n_br_invoice_serial,
                "companyLocation": AccountMove._l10n_br_edi_vat_for_api(self.journal_id.company_partner_id.vat),
                "init": self.start_number,
                "end": self.end_number,
                "message": self.reason,
            },
            self.journal_id.company_id,
        )

        # For errors and single number cancellations, Avatax returns the dict without wrapping it in a list.
        if not isinstance(responses, list):
            responses = [responses]

        attachments = self.env["ir.attachment"]
        for response in responses:
            if error := AccountMove._l10n_br_get_error_from_response(response):
                raise ValidationError(error)

            attachments |= self.env["ir.attachment"].create(
                {
                    "name": f"{self.journal_id.name} cancel {response['status']['number']}.xml",
                    "datas": response["xml"]["base64"],
                }
            )

        self.journal_id.message_post(
            body=_(
                'Cancelled range %s - %s for document type %s for reason "%s".',
                self.start_number,
                self.end_number,
                self.document_type_id.display_name,
                self.reason,
            ),
            attachment_ids=attachments.ids,
        )
