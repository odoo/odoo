# Part of Odoo. See LICENSE file for full copyright and licensing details.
from textwrap import dedent

from markupsafe import Markup

from odoo import api, models, fields, _
from odoo.addons.iap import InsufficientCreditError
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_br_last_edi_status = fields.Selection(selection_add=[("pending", "Pending")])
    l10n_br_nfse_number = fields.Char(
        "NFS-e Number",
        help="Brazil: After an NFS-e invoice is issued and confirmed by the municipality, an NFS-e number is provided.",
    )
    l10n_br_nfse_verification = fields.Char(
        "NFS-e Verification Code",
        help="Brazil: After an NFS-e invoice is issued and confirmed by the municipality, a unique code is provided for online verification of its authenticity.",
    )

    @api.depends("l10n_br_last_edi_status")
    def _compute_show_reset_to_draft_button(self):
        """Override. Don't show resetting to draft when the invoice is pending. It's already been sent and the user
        should wait for the final result of that."""
        super()._compute_show_reset_to_draft_button()
        self.filtered(lambda move: move.l10n_br_last_edi_status == "pending").write(
            {"show_reset_to_draft_button": False}
        )

    def button_l10n_br_edi_get_service_invoice(self):
        """Checks if the invoice received final approval from the government."""
        if self.l10n_br_last_edi_status != "pending":
            return

        response = self._l10n_br_iap_request(
            "get_invoice_services",
            {
                "serie": self.journal_id.l10n_br_invoice_serial,
                "number": self.l10n_latam_document_number,
            },
        )
        if error := self._l10n_br_get_error_from_response(response):
            self.l10n_br_last_edi_status = "error"
            self.l10n_br_edi_error = error
            self.with_context(no_new_invoice=True).message_post(body=_("E-invoice was not accepted:\n%s", error))
            return

        status = response.get("status", {})
        response_code = status.get("code")
        attachments = self.env["ir.attachment"]
        subtype_xmlid = None
        if response_code == "105":
            message = _("E-invoice is pending: %s", status.get("desc"))
        elif response_code in ("100", "200"):
            self.l10n_br_last_edi_status = "accepted"
            self.l10n_br_nfse_number = status.get("nfseNumber")
            self.l10n_br_nfse_verification = status.get("nfseVerifyCode")

            message = (
                Markup(
                    dedent(
                        """
                        %s
                        <ul>
                          <li>%s</li>
                          <li>%s</li>
                          <li>%s</li>
                        </ul>
                        """
                    )
                )
                % (
                    _("E-invoice accepted:"),
                    _("Status: %s") % status.get("desc"),
                    _("NFS-e number: %s") % self.l10n_br_nfse_number,
                    _("NFS-e verify code: %s") % self.l10n_br_nfse_verification,
                )
            )
            attachments = self._l10n_br_edi_attachments_from_response(response)
            subtype_xmlid = "mail.mt_comment"  # send to all followers
        else:
            message = _("Unknown E-invoice status code %s: %s", response_code, status.get("desc"))

        self.with_context(no_new_invoice=True).message_post(
            body=message, attachment_ids=attachments.ids, subtype_xmlid=subtype_xmlid
        )

    def _l10n_br_log_informative_taxes(self, payload):
        informative_taxes = payload.get("summary", {}).get("taxImpactHighlights", {}).get("informative", [])
        # Informative taxes look like: [{"taxType": "aproxtribCity", "tax": 7.8, "subtotalTaxable": 200}, ...]
        # Transform to:
        # - taxType: aproxtribCity, tax: 7.8, subtotalTaxable: 200
        # - ...
        pretty_informative_taxes = Markup()
        for tax in informative_taxes:
            line = ", ".join(f"{key}: {value}" for key, value in tax.items())
            pretty_informative_taxes += Markup("<li>%s</li>") % line

        self.with_context(no_new_invoice=True).message_post(
            body=Markup("%s<ul>%s</ul>")
            % (_("Informative taxes:"), pretty_informative_taxes or Markup("<li>%s</li>") % _("N/A"))
        )

    def _l10n_br_prepare_invoice_payload(self):
        """Override."""
        payload, errors = super()._l10n_br_prepare_invoice_payload()
        if not self.l10n_br_is_service_transaction:
            return payload, errors

        payload["header"].update(
            {
                "rpsNumber": payload["header"]["invoiceNumber"],
                "rpsSerie": payload["header"]["invoiceSerial"],
            }
        )
        del payload["header"]["invoiceNumber"]
        del payload["header"]["invoiceSerial"]
        del payload["header"]["goods"]
        del payload["header"]["locations"]["transporter"]

        # Remove informative taxes when submitting the invoice. These informative taxes change after invoice posting,
        # based on when a customer pays. These need to be handled manually in a separate misc journal entry when needed,
        # and should not be included in the legal XML and PDF.
        self._l10n_br_log_informative_taxes(payload)

        for line in payload.get("lines", []):
            line["taxDetails"] = [
                detail for detail in line["taxDetails"] if detail["taxImpact"]["impactOnFinalPrice"] != "Informative"
            ]

        tax_highlights = payload.get("summary", {}).get("taxImpactHighlights", {})
        if "informative" in tax_highlights:
            for informative_tax in tax_highlights.get("informative", []):
                del payload["summary"]["taxByType"][informative_tax["taxType"]]

            del tax_highlights["informative"]

        return payload, errors

    def _l10n_br_edi_set_successful_status(self):
        """Override."""
        if self.l10n_br_is_service_transaction:
            self.l10n_br_last_edi_status = "pending"
        else:
            return super()._l10n_br_edi_set_successful_status()

    def _l10n_br_submit_invoice(self, invoice, payload):
        """Override."""
        if self.l10n_br_is_service_transaction:
            try:
                response = invoice._l10n_br_iap_request("submit_invoice_services", payload)
                return response, self._l10n_br_get_error_from_response(response)
            except (UserError, InsufficientCreditError) as e:
                # These exceptions can be thrown by iap_jsonrpc()
                return None, str(e)
        else:
            return super()._l10n_br_submit_invoice(invoice, payload)

    def _cron_l10n_br_get_invoice_statuses(self, batch_size=10):
        pending_invoices = self.search([("l10n_br_last_edi_status", "=", "pending")], limit=batch_size)
        for invoice in pending_invoices[:batch_size]:
            invoice.button_l10n_br_edi_get_service_invoice()

        if len(pending_invoices) > batch_size:
            self.env.ref("l10n_br_edi_services.ir_cron_l10n_br_edi_check_status")._trigger()
