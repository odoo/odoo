from lxml.builder import E

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_ge_edi.tools.rsge_client import (
    KIND_NOT_SUBMITTED,
    RSgeError,
    from_rsge_datetime,
    get_rsge_invoice_status,
    translate_rsge_error,
)

# every other state only moves through an Odoo action, which refreshes the record itself
RSGE_AWAITING_COUNTERPARTY_STATES = ["sent", "correction_pending_confirmation", "cancel_requested"]


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ge_edi_state = fields.Selection(
        selection=[
            ("not_sent", "Not Sent"),
            ("error", "Error"),
            ("rejected", "Rejected"),
            ("sent", "Sent"),
            ("confirmed", "Confirmed"),
            ("corrected_original", "Original Invoice (Corrected)"),
            ("new_correction", "New Corrective Invoice"),
            ("rejected_correction", "Corrective Invoice Rejected"),
            ("correction_pending_confirmation", "Corrective Invoice - Pending Confirmation"),
            ("cancel_requested", "Cancel Requested"),
            ("confirmed_cancelled", "Cancellation Confirmed"),
            ("confirmed_correction", "Corrective Invoice Confirmed"),
            ("unknown", "Unknown"),
        ],
        string="RS.ge Status",
        readonly=True,
        copy=False,
        default="not_sent",
    )
    l10n_ge_edi_invoice_id = fields.Char(string="RS.ge Invoice Id", readonly=True, copy=False)
    l10n_ge_edi_f_series = fields.Char(string="RS.ge F-Series", readonly=True, copy=False)
    l10n_ge_edi_f_number = fields.Char(string="RS.ge F-Number", readonly=True, copy=False)
    l10n_ge_edi_registration_date = fields.Datetime(string="RS.ge Registration Date", readonly=True, copy=False)
    l10n_ge_edi_k_type = fields.Selection(
        selection=[
            ("1", "Taxable Transaction Cancelled"),
            ("3", "Compensation Amount Changed"),
            ("4", "Goods/Services Returned"),
        ],
        string="RS.ge Correction Type",
        readonly=True,
        copy=False,
    )
    l10n_ge_edi_original_move_id = fields.Many2one(comodel_name="account.move", string="RS.ge Original Invoice", readonly=True, copy=False)
    l10n_ge_edi_correction_move_id = fields.Many2one(comodel_name="account.move", string="RS.ge Corrective Invoice", readonly=True, copy=False)
    l10n_ge_edi_k_invoice_not_allowed = fields.Boolean(compute="_compute_l10n_ge_edi_k_invoice_not_allowed")
    l10n_ge_edi_request_cancellation_not_allowed = fields.Boolean(compute="_compute_l10n_ge_edi_request_cancellation_not_allowed")
    l10n_ge_edi_credit_note_not_allowed = fields.Boolean(compute="_compute_l10n_ge_edi_credit_note_not_allowed")
    l10n_ge_edi_state_not_visible = fields.Boolean(compute="_compute_l10n_ge_edi_state_not_visible")

    @api.depends("l10n_ge_edi_state", "move_type", "l10n_ge_edi_k_type", "country_code")
    def _compute_l10n_ge_edi_k_invoice_not_allowed(self):
        for move in self:
            if move.country_code != "GE" or move.move_type != "out_invoice":
                move.l10n_ge_edi_k_invoice_not_allowed = True
            elif move.l10n_ge_edi_k_type:
                move.l10n_ge_edi_k_invoice_not_allowed = move.l10n_ge_edi_state != "confirmed_correction"
            else:
                move.l10n_ge_edi_k_invoice_not_allowed = move.l10n_ge_edi_state != "confirmed"

    @api.depends("l10n_ge_edi_state", "move_type", "l10n_ge_edi_k_type", "country_code")
    def _compute_l10n_ge_edi_request_cancellation_not_allowed(self):
        for move in self:
            if move.country_code != "GE":
                move.l10n_ge_edi_request_cancellation_not_allowed = True
            elif move.move_type == "out_invoice" and move.l10n_ge_edi_k_type:
                move.l10n_ge_edi_request_cancellation_not_allowed = move.l10n_ge_edi_state != "confirmed_correction"
            elif move.move_type == "out_invoice":
                move.l10n_ge_edi_request_cancellation_not_allowed = move.l10n_ge_edi_state != "confirmed"
            elif move.move_type == "out_refund" and move.l10n_ge_edi_k_type == "4":
                move.l10n_ge_edi_request_cancellation_not_allowed = move.l10n_ge_edi_state != "confirmed_correction"
            else:
                move.l10n_ge_edi_request_cancellation_not_allowed = True

    @api.depends("l10n_ge_edi_state", "country_code")
    def _compute_l10n_ge_edi_credit_note_not_allowed(self):
        for move in self:
            move.l10n_ge_edi_credit_note_not_allowed = (
                move.country_code == "GE" and move.l10n_ge_edi_state != "not_sent"
            )

    @api.depends("l10n_ge_edi_state", "state", "move_type", "country_code")
    def _compute_l10n_ge_edi_state_not_visible(self):
        for move in self:
            move.l10n_ge_edi_state_not_visible = not (
                move.country_code == "GE"
                and move.move_type in {"out_invoice", "out_refund"}
                and (move.state == "posted" or move.l10n_ge_edi_state in {"confirmed_cancelled", "corrected_original"})
            )

    def _l10n_ge_edi_reset_draft_not_allowed(self):
        self.ensure_one()
        if self.country_code != "GE" or self.move_type not in {"out_invoice", "out_refund"}:
            return False
        if self.l10n_ge_edi_k_type == "1":
            return True
        if self.l10n_ge_edi_state in {"not_sent", "error", "rejected", "new_correction", "rejected_correction"}:
            return False
        if self.l10n_ge_edi_state == "confirmed_cancelled" and self.state != "cancel":
            return False
        return not (
            self.l10n_ge_edi_state == "corrected_original"
            and self.state != "cancel"
            and self.l10n_ge_edi_correction_move_id.l10n_ge_edi_k_type == "3"
        )

    @api.depends(
        "l10n_ge_edi_state", "state", "move_type", "country_code",
        "l10n_ge_edi_k_type", "l10n_ge_edi_correction_move_id.l10n_ge_edi_k_type",
    )
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move._l10n_ge_edi_reset_draft_not_allowed():
                move.show_reset_to_draft_button = False

    def button_draft(self):
        # EXTENDS 'account'
        if any(move._l10n_ge_edi_reset_draft_not_allowed() for move in self):
            raise UserError(self.env._("Invoice sent to RS.ge cannot be reset to draft."))
        return super().button_draft()

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type="form", **options):
        # EXTENDS base: the RS.ge columns below are injected per company
        return super()._get_view_cache_key(view_id, view_type, **options) + (self.env.company.country_code,)

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        # EXTENDS base
        arch, view = super()._get_view(view_id, view_type, **options)
        is_invoice_list = view_type == "list" and arch.find("./field[@name='move_type']") is not None
        if not is_invoice_list or self.env.company.country_code != "GE":
            return arch, view

        anchor = arch.find("./field[@name='name']")
        if anchor is not None:
            for field_name, label in (("l10n_ge_edi_f_series", self.env._("F-Series")), ("l10n_ge_edi_f_number", self.env._("F-Number"))):
                anchor.addnext(E.field(name=field_name, string=label, optional="show"))
                anchor = anchor.getnext()

        invoice_date = arch.find("./field[@name='invoice_date']")
        if invoice_date is not None:
            invoice_date.addprevious(E.field(
                name="l10n_ge_edi_registration_date",
                string=self.env._("Submitted On"),
                # RS.ge's time is worth storing, but the column reads as a date next to the invoice date
                options="{'show_time': False}",
                optional="show",
            ))
        return arch, view

    def action_l10n_ge_edi_refresh_status(self):
        self.ensure_one()
        company = self.company_id
        client = company._l10n_ge_edi_get_client()
        try:
            invoice_data = client.get_invoice(user_id=company.sudo().l10n_ge_edi_user_id, invoice_id=self._l10n_ge_edi_get_invoice_id())
        except RSgeError as error:
            self.message_post(body=translate_rsge_error(self.env, error))
            return

        previous_state = self.l10n_ge_edi_state
        self.l10n_ge_edi_state = get_rsge_invoice_status(invoice_data["status"], invoice_data["f_number"])
        self.l10n_ge_edi_registration_date = from_rsge_datetime(invoice_data["reg_dt"])
        if previous_state != "confirmed_cancelled" and self.l10n_ge_edi_state == "confirmed_cancelled":
            self.button_cancel()
            if self.l10n_ge_edi_original_move_id:
                self.l10n_ge_edi_original_move_id.action_l10n_ge_edi_refresh_status()

    def action_l10n_ge_edi_open_original_move(self):
        self.ensure_one()
        return self.l10n_ge_edi_original_move_id._get_records_action(name=self.env._("Original Invoice"))

    def action_l10n_ge_edi_open_correction_move(self):
        self.ensure_one()
        return self.l10n_ge_edi_correction_move_id._get_records_action(name=self.env._("Corrective Invoice"))

    def action_l10n_ge_edi_open_k_invoice_wizard(self):
        self.ensure_one()
        if self.l10n_ge_edi_k_invoice_not_allowed:
            raise UserError(
                self.env._("This invoice must be confirmed by RS.ge before a corrective invoice can be created."),
            )
        return {
            "name": self.env._("Choose K Invoice Type"),
            "type": "ir.actions.act_window",
            "res_model": "l10n_ge_edi.k_invoice.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_move_id": self.id},
        }

    def action_l10n_ge_edi_request_cancellation(self):
        self.ensure_one()
        if self.l10n_ge_edi_request_cancellation_not_allowed:
            raise UserError(
                self.env._("This invoice must be confirmed by RS.ge before a cancellation can be requested."),
            )
        if self._l10n_ge_edi_has_reconciled_payment():
            raise UserError(
                self.env._(
                    "This invoice has reconciled payments and cannot be cancelled, since that "
                    "would incorrectly unreconcile the payment. Use K Invoice's Cancel "
                    "Transaction instead, which creates a credit note.",
                ),
            )

        company = self.company_id
        client = company._l10n_ge_edi_get_client()
        user_id = company.sudo().l10n_ge_edi_user_id

        try:
            invoice_id = self._l10n_ge_edi_get_invoice_id()
            client.change_invoice_status(user_id=user_id, invoice_id=invoice_id, status=6)
            invoice_data = client.get_invoice(user_id=user_id, invoice_id=invoice_id)
        except RSgeError as error:
            raise UserError(translate_rsge_error(self.env, error)) from error

        self.l10n_ge_edi_state = get_rsge_invoice_status(invoice_data["status"], invoice_data["f_number"])
        self.message_post(body=self.env._("Cancellation requested from RS.ge."))

    @api.model
    def _l10n_ge_edi_refresh_all_statuses(self):
        invoices_to_update = self.search(
            [("move_type", "in", ["out_invoice", "out_refund"]), ("l10n_ge_edi_state", "in", RSGE_AWAITING_COUNTERPARTY_STATES)],
        )
        for company, invoices in invoices_to_update.grouped("company_id").items():
            company_sudo = company.sudo()
            if not (company_sudo.l10n_ge_edi_su and company_sudo.l10n_ge_edi_sp):
                continue
            for invoice in invoices:
                invoice.action_l10n_ge_edi_refresh_status()

    def _l10n_ge_edi_has_reconciled_payment(self):
        self.ensure_one()
        partials = self.line_ids.matched_debit_ids | self.line_ids.matched_credit_ids
        counterparts = (partials.debit_move_id | partials.credit_move_id) - self.line_ids
        return bool(counterparts - self.reversed_entry_id.line_ids)

    def _l10n_ge_edi_get_invoice_id(self):
        """Return the RS.ge header id as the int the API expects, for an invoice already registered there."""
        self.ensure_one()
        if not self.l10n_ge_edi_invoice_id:
            raise RSgeError(KIND_NOT_SUBMITTED)
        return int(self.l10n_ge_edi_invoice_id)

    def _l10n_ge_edi_matches_rsge(self, remote_header):
        self.ensure_one()
        return (
            remote_header["operation_dt"].date() == (self.invoice_date or self.date)
            and remote_header["seller_un_id"] == int(self.company_id.partner_id.l10n_ge_edi_un_id)
            and remote_header["buyer_un_id"] == int(self.partner_id.l10n_ge_edi_un_id)
        )

    def _l10n_ge_edi_submit_correction(self):
        """Register this correction with RS.ge, returning the `RSgeError` it failed on, or nothing on success."""
        self.ensure_one()
        company = self.company_id
        client = company._l10n_ge_edi_get_client()
        user_id = company.sudo().l10n_ge_edi_user_id
        lines = self.invoice_line_ids.filtered(lambda line: line.display_type == "product")

        try:
            invoice_id = self._l10n_ge_edi_get_invoice_id()
            remote_lines_by_id = {
                row["ID"]: row for row in client.get_invoice_lines(user_id=user_id, invoice_id=invoice_id)
            }
            stale_line_ids = remote_lines_by_id.keys() - set(lines.mapped("l10n_ge_edi_line_id"))
            for stale_line_id in stale_line_ids:
                client.delete_invoice_line(user_id=user_id, invoice_id=invoice_id, line_id=int(stale_line_id))

            for line in lines:
                remote_line = remote_lines_by_id.get(line.l10n_ge_edi_line_id)
                if remote_line and line._l10n_ge_edi_matches_rsge(remote_line):
                    continue

                line_id = client.save_invoice_line(
                    user_id=user_id,
                    invoice_id=invoice_id,
                    line_id=int(line.l10n_ge_edi_line_id or 0),
                    goods=line.name or line.product_id.display_name,
                    g_unit=line.product_uom_id.name or "pcs",
                    g_number=line.quantity,
                    full_amount=line.price_total,
                    drg_amount=line._l10n_ge_edi_drg_amount(),
                )
                line.l10n_ge_edi_line_id = str(line_id)

            client.change_invoice_status(user_id=user_id, invoice_id=invoice_id, status=5)
            invoice_data = client.get_invoice(user_id=user_id, invoice_id=invoice_id)
        except RSgeError as error:
            self.l10n_ge_edi_state = "error"
            self.message_post(body=translate_rsge_error(self.env, error))
            return error

        self.write(
            {
                "l10n_ge_edi_state": get_rsge_invoice_status(invoice_data["status"], invoice_data["f_number"]),
                "l10n_ge_edi_f_series": invoice_data["f_series"],
                "l10n_ge_edi_f_number": invoice_data["f_number"],
                "l10n_ge_edi_registration_date": from_rsge_datetime(invoice_data["reg_dt"]),
            },
        )
        message = self.env._(
            "Corrective invoice sent to RS.ge (%(f_series)s-%(f_number)s).",
            f_series=invoice_data["f_series"],
            f_number=invoice_data["f_number"],
        )
        self.message_post(body=message)

    def _l10n_ge_edi_submit_k_invoice_type_1(self):
        """Send an already-created Cancel Transaction correction, returning the `RSgeError` or nothing."""
        self.ensure_one()
        company = self.company_id
        client = company._l10n_ge_edi_get_client()
        user_id = company.sudo().l10n_ge_edi_user_id

        try:
            invoice_id = self._l10n_ge_edi_get_invoice_id()
            client.change_invoice_status(user_id=user_id, invoice_id=invoice_id, status=5)
            invoice_data = client.get_invoice(user_id=user_id, invoice_id=invoice_id)
        except RSgeError as error:
            self.l10n_ge_edi_state = "error"
            self.message_post(body=translate_rsge_error(self.env, error))
            return error

        self.write(
            {
                "l10n_ge_edi_state": get_rsge_invoice_status(invoice_data["status"], invoice_data["f_number"]),
                "l10n_ge_edi_f_series": invoice_data["f_series"],
                "l10n_ge_edi_f_number": invoice_data["f_number"],
                "l10n_ge_edi_registration_date": from_rsge_datetime(invoice_data["reg_dt"]),
            },
        )
        message = self.env._(
            "Corrective invoice sent to RS.ge (%(f_series)s-%(f_number)s).",
            f_series=invoice_data["f_series"],
            f_number=invoice_data["f_number"],
        )
        self.message_post(body=message)

    def _l10n_ge_edi_submit_invoice(self):
        """Register this invoice with RS.ge, returning the `RSgeError` it failed on, or nothing on success."""
        self.ensure_one()
        if self.l10n_ge_edi_k_type:
            if self.l10n_ge_edi_k_type == "1":
                return self._l10n_ge_edi_submit_k_invoice_type_1()
            return self._l10n_ge_edi_submit_correction()

        company = self.company_id
        client = company._l10n_ge_edi_get_client()
        user_id = company.sudo().l10n_ge_edi_user_id
        lines = self.invoice_line_ids.filtered(lambda line: line.display_type == "product")

        try:
            invoice_id = int(self.l10n_ge_edi_invoice_id or 0)
            remote_header = False
            remote_lines_by_id = {}
            if invoice_id:
                remote_header = client.get_invoice(user_id=user_id, invoice_id=invoice_id)
                remote_lines_by_id = {
                    row["ID"]: row for row in client.get_invoice_lines(user_id=user_id, invoice_id=invoice_id)
                }
                stale_line_ids = remote_lines_by_id.keys() - set(lines.mapped("l10n_ge_edi_line_id"))
                for stale_line_id in stale_line_ids:
                    client.delete_invoice_line(user_id=user_id, invoice_id=invoice_id, line_id=int(stale_line_id))

            operation_date = self.invoice_date or self.date
            seller_un_id = int(company.partner_id.l10n_ge_edi_un_id)
            buyer_un_id = int(self.partner_id.l10n_ge_edi_un_id)
            if not remote_header or not self._l10n_ge_edi_matches_rsge(remote_header):
                invoice_id = client.save_invoice(
                    user_id=user_id,
                    invoice_id=invoice_id,
                    operation_date=operation_date,
                    seller_un_id=seller_un_id,
                    buyer_un_id=buyer_un_id,
                )
                self.l10n_ge_edi_invoice_id = str(invoice_id)

            for line in lines:
                remote_line = remote_lines_by_id.get(line.l10n_ge_edi_line_id)
                if remote_line and line._l10n_ge_edi_matches_rsge(remote_line):
                    continue

                line_id = client.save_invoice_line(
                    user_id=user_id,
                    invoice_id=invoice_id,
                    line_id=int(line.l10n_ge_edi_line_id or 0),
                    goods=line.name or line.product_id.display_name,
                    g_unit=line.product_uom_id.name or "pcs",
                    g_number=line.quantity,
                    full_amount=line.price_total,
                    drg_amount=line._l10n_ge_edi_drg_amount(),
                )
                line.l10n_ge_edi_line_id = str(line_id)

            client.change_invoice_status(user_id=user_id, invoice_id=invoice_id, status=1)
            invoice_data = client.get_invoice(user_id=user_id, invoice_id=invoice_id)
        except RSgeError as error:
            self.l10n_ge_edi_state = "error"
            self.message_post(body=translate_rsge_error(self.env, error))
            return error

        self.write(
            {
                "l10n_ge_edi_state": get_rsge_invoice_status(invoice_data["status"], invoice_data["f_number"]),
                "l10n_ge_edi_f_series": invoice_data["f_series"],
                "l10n_ge_edi_f_number": invoice_data["f_number"],
                "l10n_ge_edi_registration_date": from_rsge_datetime(invoice_data["reg_dt"]),
            },
        )
        message = self.env._(
            "Invoice sent to RS.ge (%(f_series)s-%(f_number)s).",
            f_series=invoice_data["f_series"],
            f_number=invoice_data["f_number"],
        )
        self.message_post(body=message)
