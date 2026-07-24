import logging
from datetime import timedelta
from json import JSONDecodeError
from urllib.parse import quote

from markupsafe import Markup

from odoo import Command, _, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.l10n_tr_nilvera.lib.nilvera_client import _get_nilvera_client

_logger = logging.getLogger(__name__)

TICARIFATURA_ANSWER_TO_FIELD_VALUE_MAP = {
    "approved": "commercial_approved",
    "rejected": "commercial_rejected",
    "documentAnsweredAutomatically": "commercial_answered_automatically",
}

UNSYNCED_COMMERCIAL_MOVE_DOMAIN = [
    ("move_type", "in", ["out_invoice", "in_invoice"]),
    ("l10n_tr_gib_invoice_scenario", "=", "TICARIFATURA"),
    ("l10n_tr_nilvera_send_status", "=", "succeed"),
    ("partner_id", "!=", False),  # Partner's status is needed to determine endpoint when fetching response
    ("company_id.partner_id.country_id.code", "=", "TR"),
    ("company_id.l10n_tr_nilvera_api_key", "!=", False),
]


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_tr_nilvera_send_status = fields.Selection(
        selection_add=[
            ("commercial_approved", "Approved (Commercial)"),
            ("commercial_answered_automatically", "Approved Automatically (Commercial)"),
            ("commercial_rejected", "Rejected (Commercial)"),
        ],
        ondelete={
            "commercial_approved": "set default",
            "commercial_answered_automatically": "set default",
            "commercial_rejected": "set default",
        },
    )
    l10n_tr_gib_invoice_scenario = fields.Selection(
        selection_add=[
            ("TICARIFATURA", "Commercial"),
        ],
        ondelete={"TICARIFATURA": "set default"},
    )
    l10n_tr_gib_invoice_type = fields.Selection(
        selection_add=[
            ("IADE", "Return"),
            ("TEVKIFATIADE", "Withholding Return"),
        ],
        ondelete={"IADE": "set default", "TEVKIFATIADE": "set default"},
    )
    l10n_tr_original_invoice_date = fields.Date(string="Original Invoice Date")
    l10n_tr_ticarifatura_last_checked_at = fields.Datetime(
        string="Commercial Status Check Date",
        copy=False,
    )

    def _l10n_tr_nilvera_check_reset_to_draft(self):
        for move in self.filtered(lambda move: move.l10n_tr_nilvera_uuid and move.move_type in {"out_invoice", "in_invoice"}):
            if move.l10n_tr_nilvera_send_status == "error":
                move.message_post(
                    body=_(
                        "To preserve accounting integrity and comply with legal requirements, invoices cannot be reused once an error occurs. Please create a new invoice to continue."
                    )
                )
            elif move.l10n_tr_nilvera_send_status not in {"not_sent", "commercial_rejected"}:
                raise UserError(_("You cannot reset to draft an entry that has been sent/received from Nilvera."))

    def _l10n_tr_nilvera_einvoice_check_invalid_invoice_reference(self):
        invalid_moves = self.env["account.move"]
        for record in self:
            _, parts = record._get_sequence_format_param(record.ref or "")
            if (
                record.move_type == "out_refund"
                and not record.reversed_entry_id
                and not (parts["prefix1"][:3] and parts["year"] and parts["seq"])
            ):
                invalid_moves |= record
        return invalid_moves

    def _l10n_tr_nilvera_check_invalid_type(self):
        invalid_invoices = self.env["account.move"]
        for record in self:
            if record.l10n_tr_gib_invoice_type in {"IADE", "TEVKIFATIADE"} ^ record.move_type == "out_refund":
                invalid_invoices |= record
        return invalid_invoices

    def _l10n_tr_nilvera_get_submitted_document_status(self):
        # OVERRIDES l10n_tr_nilvera_einvoice to handle the customer response on
        # TICARIFATURA documents.
        for company, invoices in self.grouped("company_id").items():
            with _get_nilvera_client(company) as client:
                for invoice in invoices:
                    invoice_channel = invoice.partner_id.l10n_tr_nilvera_customer_status
                    document_category = invoice._l10n_tr_get_document_category(invoice_channel)
                    if not document_category or not invoice_channel:
                        continue

                    response = client.request(
                        "GET",
                        f"/{invoice_channel}/{quote(document_category)}/{invoice.l10n_tr_nilvera_uuid}/Status",
                    )

                    nilvera_status = response.get("InvoiceStatus", {}).get("Code") or response.get("StatusCode")
                    if nilvera_status in dict(invoice._fields["l10n_tr_nilvera_send_status"].selection):
                        if nilvera_status == "error":
                            invoice.message_post(
                                body=Markup("%s<br/>%s - %s<br/>")
                                % (
                                    _("The invoice couldn't be sent to the recipient."),
                                    response.get("InvoiceStatus", {}).get("Description") or response.get("StatusDetail"),
                                    response.get("InvoiceStatus", {}).get("DetailDescription") or response.get("ReportStatus"),
                                )
                            )
                        elif (
                            invoice.l10n_tr_gib_invoice_scenario == "TICARIFATURA"
                            and invoice.move_type in {"out_invoice", "in_invoice"}
                            and nilvera_status == "succeed"
                        ):
                            if response["Answer"] and response["Answer"].get("AnswerCode") in {
                                "approved",
                                "rejected",
                                "documentAnsweredAutomatically",
                            }:
                                invoice.l10n_tr_nilvera_send_status = TICARIFATURA_ANSWER_TO_FIELD_VALUE_MAP[
                                    response["Answer"]["AnswerCode"]
                                ]
                                if response["Answer"]["AnswerCode"] == "rejected":
                                    invoice._l10n_tr_action_process_rejected_ticarifatura(
                                        response["Answer"].get("Description", ""), client
                                    )
                        else:
                            invoice.l10n_tr_nilvera_send_status = nilvera_status
                    else:
                        invoice.message_post(body=_("The invoice status couldn't be retrieved from Nilvera."))

    def _get_starting_sequence(self):
        """
        Generate a valid name for credit notes.

        Nilvera requires invoice names in the format:
        <3 alphanumeric characters>/<year>/<sequence number>.

        When creating a credit note, an R is added by standard, so
        we remove the first letter of the journal prefix to make sure it
        remains 3 characters (e.g., RINV → RNV).
        """
        starting_sequence = super()._get_starting_sequence()
        if (
            self.company_id.country_id.code == "TR"
            and self.journal_id.refund_sequence
            and self.move_type in {"out_refund", "in_refund"}
        ):
            starting_sequence = starting_sequence[0] + starting_sequence[2:]
        return starting_sequence

    def _reverse_moves(self, default_values_list=None, cancel=False):
        if all(move.country_code != "TR" or move.move_type != "out_invoice" for move in self):
            return super()._reverse_moves(default_values_list, cancel=cancel)

        if not default_values_list:
            default_values_list = [{}] * len(self)

        for default_vals, move in zip(default_values_list, self):
            if move.country_code != "TR" or move.move_type != "out_invoice":
                continue
            line_vals = move.line_ids.copy_data()
            for line, vals in zip(move.line_ids, line_vals):
                vals.update(
                    {
                        "l10n_tr_original_line_id": line.id,
                        "l10n_tr_original_quantity": line.quantity,
                        "l10n_tr_original_tax_without_withholding": line.price_total - line.price_subtotal,
                    },
                )
            default_vals.update(
                {
                    "ref": move.name,
                    "l10n_tr_gib_invoice_scenario": "TEMELFATURA",
                    "l10n_tr_gib_invoice_type": "TEVKIFATIADE" if move.l10n_tr_gib_invoice_type == "TEVKIFAT" else "IADE",
                    "line_ids": [Command.create(vals) for vals in line_vals],
                },
            )

        return super()._reverse_moves(default_values_list, cancel=cancel)

    def _l10n_tr_handle_409_error_for_send_answer(self, response):
        self.ensure_one()
        error_codes_to_handle = {1003, 1007, 1008, 1011}
        for error in response["Errors"]:
            # These error means, the move was responded to already
            # Thus we sync now
            if error.get("Code") in error_codes_to_handle:
                self.l10n_tr_action_fetch_ticarifatura_response()
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "message": self.env._(
                            "Nilvera has already received a response for this invoice."
                            "\nThe latest response has been fetched and updated on the invoice.",
                        ),
                        "type": "warning",
                        "next": {"type": "ir.actions.client", "tag": "soft_reload"},
                    },
                }
        errors = [f"{error.get('Code')}: {error.get('Description')}" for error in response["Errors"]]
        raise ValidationError(self.env._("Error sending request:\n%s", "\n".join(errors)))

    def _l10n_tr_action_send_ticarifatura_response(self, answer_code="approved", rejection_note=""):
        self.ensure_one()
        if self.move_type != "in_invoice" or self.l10n_tr_gib_invoice_scenario != "TICARIFATURA":
            raise UserError(self.env._("This action is only available for commercial bills."))
        if self.l10n_tr_nilvera_send_status != "succeed":
            raise UserError(self.env._("The bill must be in 'Successful' status before sending a response."))

        with _get_nilvera_client(self.env.company) as client:
            response = client.request(
                method="POST",
                endpoint="/einvoice/Purchase/SendAnswer",
                json={
                    "UUID": self.l10n_tr_nilvera_uuid,
                    "AnswerCode": answer_code,
                    "RejectNote": rejection_note,
                },
                handle_response=False,
            )

            if response.status_code == 200:
                self.l10n_tr_nilvera_send_status = TICARIFATURA_ANSWER_TO_FIELD_VALUE_MAP[answer_code]
                if answer_code == "rejected":
                    self._l10n_tr_action_process_rejected_ticarifatura(rejection_note, client)
            elif response.status_code in {401, 403}:
                raise UserError(
                    self.env._(
                        "Oops, seems like you're unauthorised to do this. Try another API key with more rights or contact Nilvera."
                    )
                )
            elif 403 < response.status_code < 600 and response.status_code != 409:
                raise UserError(
                    self.env._(
                        "Odoo could not perform this action at the moment, try again later.\n%(reason)s - %(status)s",
                        reason=response.reason,
                        status=response.status_code,
                    ),
                )
            elif response.status_code == 409:
                try:
                    decoded_response = response.json()
                except JSONDecodeError:
                    _logger.exception("Invalid JSON response: %s", response.text)
                    raise UserError(self.env._("An error occurred. Try again later."))
                return self._l10n_tr_handle_409_error_for_send_answer(decoded_response)
            return True

    def _l10n_tr_action_process_rejected_ticarifatura(self, rejection_note, client):
        self.ensure_one()
        responder = self.partner_id if self.move_type == "out_invoice" else self.company_id
        self.message_post(
            body=Markup("""
                <div class="border-start border-danger border-3 ps-3 py-2 bg-opacity-10 rounded">
                    <strong class="text-danger">❌ Rejected</strong>
                    <p class="mb-0 mt-1">
                        <strong>Responder:</strong> %s <br/>
                        <strong>Reason:</strong> %s
                    </p>
                </div>
            """)
            % (
                responder.name,
                rejection_note,
            ),
            message_type="notification",
            subtype_xmlid="mail.mt_note",
        )
        if self.move_type == "out_invoice":
            self._l10n_tr_nilvera_add_pdf_to_invoice(
                client,
                self,
                self.l10n_tr_nilvera_uuid,
                document_category="Sale",
                invoice_channel=self.l10n_tr_nilvera_customer_status,
            )
        self.filtered(lambda m: m.state == "posted").button_draft()
        self.button_cancel()

    def l10n_tr_action_fetch_ticarifatura_response(self):
        self.ensure_one()

        if self.move_type not in {"out_invoice", "in_invoice"} or self.l10n_tr_gib_invoice_scenario != "TICARIFATURA":
            raise UserError(self.env._("This action is only available for Commercial Invoices/Bills."))
        if self.l10n_tr_nilvera_send_status in {
            "commercial_approved",
            "commercial_answered_automatically",
            "commercial_rejected",
        }:
            raise UserError(self.env._("The response has already been received for this invoice."))
        if self.l10n_tr_nilvera_send_status != "succeed":
            raise UserError(self.env._("The invoice is not approved by Nilvera yet."))

        return self._l10n_tr_nilvera_get_submitted_document_status()

    def l10n_tr_action_approve_ticarifatura(self):
        self.ensure_one()
        return self.env["l10n_tr.ticarifatura.response.wizard"]._get_records_action(
            name=self.env._("Accept Bill"),
            target="new",
            context={
                **self.env.context,
                "default_move_id": self.id,
                "default_response_code": "approved",
            },
        )

    def l10n_tr_action_reject_ticarifatura(self):
        self.ensure_one()
        return self.env["l10n_tr.ticarifatura.response.wizard"]._get_records_action(
            name=self.env._("Reject Bill"),
            target="new",
            context={
                **self.env.context,
                "default_move_id": self.id,
                "default_response_code": "rejected",
            },
        )

    def _cron_l10n_tr_nilvera_sync_ticarifatura_response(self, *, limit=20):
        """
        Commercial invoices require a response from the counterpart within 7 days.
        After that window, Nilvera automatically accepts the invoice.

        To ensure no invoice is starved across the 7-day window, records are
        processed least recently checked first, so that every pending invoice
        gets polled evenly over time.

        :param int limit: Number of invoices to process per run. Default: 20.
        """
        _logger.info("Nilvera commercial move response sync started.")

        # This cron is run with commit. So on rerun our processed data still remain in the domain
        # As current processed data will have l10n_tr_ticarifatura_last_checked_at as now
        # With timedelta we are avoiding those
        now_minus_2_hours = fields.Datetime.now() - timedelta(hours=2)
        domain = UNSYNCED_COMMERCIAL_MOVE_DOMAIN + [
            "|",
            ("l10n_tr_ticarifatura_last_checked_at", "=", False),
            ("l10n_tr_ticarifatura_last_checked_at", "<", now_minus_2_hours),
        ]

        move_ids_to_process = self.env["account.move"].search(
            domain,
            order="l10n_tr_ticarifatura_last_checked_at asc NULLS FIRST",
            limit=limit,
        )

        if not move_ids_to_process:
            _logger.info("No commercial moves found for response sync.")
            return

        for move in move_ids_to_process:
            try:
                # UNSYNCED_COMMERCIAL_MOVE_DOMAIN ensures the moves passed are valid
                move._l10n_tr_nilvera_get_submitted_document_status()
            except UserError as e:
                _logger.warning(
                    "Failed to fetch commercial move response for move %s: %s",
                    move.id,
                    e,
                )

            # Always update checked date, to avoid checking the same record on the same cron
            move.write({"l10n_tr_ticarifatura_last_checked_at": fields.Datetime.now()})
        remaining = 0 if len(move_ids_to_process) < limit else self.env["account.move"].search_count(domain)
        self.env["ir.cron"]._commit_progress(
            len(move_ids_to_process),
            remaining=remaining,
        )
