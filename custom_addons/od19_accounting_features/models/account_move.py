# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    # ------------------------------------------------------------------
    # Feature 1: Cancel reason
    # ------------------------------------------------------------------
    od19_cancel_reason = fields.Text(
        string="Cancel Reason",
        copy=False,
        readonly=True,
        help="Reason entered when cancelling this journal entry.",
    )

    def button_cancel(self):
        """Open the cancel-reason wizard for posted/draft moves, then cancel.

        When the wizard confirms it calls the real cancellation with the
        reason stored on the move. The wizard passes ``od19_skip_reason``
        in the context so this override does not loop.
        """
        if self.env.context.get("od19_skip_reason"):
            return super().button_cancel()

        # Only ask for a reason for moves that can be cancelled.
        cancellable = self.filtered(lambda m: m.state in ("draft", "posted"))
        if not cancellable:
            return super().button_cancel()

        return {
            "name": "Cancel Reason",
            "type": "ir.actions.act_window",
            "res_model": "od19.account.move.cancel.reason",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_ids": cancellable.ids,
                "active_model": "account.move",
            },
        }

    # ------------------------------------------------------------------
    # Feature 2: Payer / Payee on prepayments
    # ------------------------------------------------------------------
    od19_payer_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้จ่ายเงิน / Payer",
        help="Partner who actually pays for this prepayment.",
    )
    od19_payee_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้รับเงิน / Payee",
        help="Partner who actually receives this prepayment.",
    )

    od19_is_downpayment = fields.Boolean(
        string="Is Prepayment",
        compute="_compute_od19_is_downpayment",
        help="Technical helper. True when the move is a downpayment/prepayment.",
    )

    @api.depends("move_type", "invoice_line_ids")
    def _compute_od19_is_downpayment(self):
        for move in self:
            is_dp = False
            # ``is_downpayment`` stored field is added by the ``sale`` module.
            if "is_downpayment" in move._fields:
                is_dp = bool(move.is_downpayment)
            else:
                # Fallback: account module provides a method that ``sale`` overrides.
                try:
                    is_dp = move._is_downpayment()
                except Exception:
                    is_dp = False
            move.od19_is_downpayment = is_dp

    # ------------------------------------------------------------------
    # Feature 3: BOT URL link
    # ------------------------------------------------------------------
    od19_bot_url = fields.Char(
        string="BOT Link",
        compute="_compute_od19_bot_url",
        help="Revenue Department (BOT) lookup URL for this tax invoice.",
    )

    @api.depends("name", "company_id.od19_bot_url")
    def _compute_od19_bot_url(self):
        for move in self:
            base = (move.company_id.od19_bot_url or "").strip()
            if base and move.name and move.name != "/":
                sep = "&" if "?" in base else "?"
                move.od19_bot_url = "{}{}id={}".format(base, sep, move.name)
            else:
                move.od19_bot_url = False

    def action_open_bot_url(self):
        self.ensure_one()
        url = self.od19_bot_url
        if not url:
            raise UserError(
                self.env._(
                    "No BOT URL or invoice number available. "
                    "Configure the BOT URL in Settings and post the invoice first."
                )
            )
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    # ------------------------------------------------------------------
    # Feature 4: Prepayment actual due date (+30 days)
    # ------------------------------------------------------------------
    od19_actual_due_date = fields.Date(
        string="Actual Due Date",
        compute="_compute_od19_actual_due_date",
        store=True,
        help="For prepayments: invoice date + 30 days. "
        "For other moves: the standard due date.",
    )

    @api.depends("invoice_date", "invoice_date_due", "od19_is_downpayment")
    def _compute_od19_actual_due_date(self):
        for move in self:
            if move.od19_is_downpayment and move.invoice_date:
                move.od19_actual_due_date = fields.Date.add(
                    move.invoice_date, days=30
                )
            else:
                move.od19_actual_due_date = move.invoice_date_due

    # ------------------------------------------------------------------
    # Feature 5: Payment number on vendor bill
    # ------------------------------------------------------------------
    od19_payment_number = fields.Char(
        string="Payment Number",
        compute="_compute_od19_payment_number",
        help="Name(s) of the payment(s) reconciled with this vendor bill.",
    )

    @api.depends("matched_payment_ids", "line_ids.full_reconcile_id")
    def _compute_od19_payment_number(self):
        for move in self:
            names = move._get_od19_reconciled_payments().filtered(
                lambda payment: payment.name and payment.name != "/"
            ).mapped("name")
            names += move._get_od19_reconciled_refunds().filtered(
                lambda refund: refund.name and refund.name != "/"
            ).mapped("name")
            move.od19_payment_number = ", ".join(names) if names else False

    def _get_od19_reconciled_refunds(self):
        """Return the credit/debit notes reconciled with this move.

        A vendor bill can be settled by a credit note instead of a payment;
        in that case the credit note number belongs in the payment number.
        """
        self.ensure_one()
        rec_lines = self.line_ids.filtered(
            lambda line: line.account_id.reconcile and line.full_reconcile_id
        )
        if not rec_lines:
            return self.env["account.move"]
        aml = self.env["account.move.line"].search(
            [
                (
                    "full_reconcile_id",
                    "in",
                    rec_lines.mapped("full_reconcile_id").ids,
                ),
                ("move_id", "!=", self.id),
            ]
        )
        return aml.move_id.filtered(
            lambda move: move.move_type in ("out_refund", "in_refund")
        )

    def _get_od19_reconciled_payments(self):
        """Return the account.payment records linked to this move.

        Odoo exposes ``matched_payment_ids`` (payments linked through
        reconciliation) which is the most reliable source. We also fall
        back to scanning the move lines for payments that share a
        reconciliation.
        """
        self.ensure_one()
        payments = self.env["account.payment"]
        if "matched_payment_ids" in self._fields:
            payments = self.matched_payment_ids
        if not payments:
            # Fallback: find payments reconciled with the move lines.
            rec_lines = self.line_ids.filtered(
                lambda l: l.account_id.reconcile and l.full_reconcile_id
            )
            if rec_lines:
                reconcile_ids = rec_lines.mapped("full_reconcile_id").ids
                aml = self.env["account.move.line"].search(
                    [
                        ("full_reconcile_id", "in", reconcile_ids),
                        ("move_id", "!=", self.id),
                    ]
                )
                payments = aml.mapped("payment_id")
        return payments

    # ------------------------------------------------------------------
    # Feature 6: Unique supplier reference on vendor bills
    # ------------------------------------------------------------------
    # The supplier reference (``ref``) is the vendor's tax invoice number.
    # It must not be booked twice for the same vendor in the same company,
    # otherwise the payable (and the input VAT) would be recorded twice.
    # Only vendor bills/refunds are guarded, and only when a reference is
    # actually filled in (draft bills without a number are left alone).
    _od19_supplier_ref_uniq = models.UniqueIndex(
        "(company_id, commercial_partner_id, ref) WHERE ("
        "move_type IN ('in_invoice', 'in_refund') "
        "AND ref IS NOT NULL AND ref <> '')",
        lambda env, diagnostics: env._(
            "เลขที่ใบกำกับซื้อซ้ำ: คู่ค้ารายนี้มีใบแจ้งหนี้/ใบลดหนี้ที่ใช้เลขที่อ้างอิงนี้แล้วในบริษัทนี้\n"
            "Duplicate supplier reference: this partner already has a vendor bill "
            "or refund using this reference in this company."
        ),
    )

    # ------------------------------------------------------------------
    # Feature 7: Central reconciliation helper (ตัดบัญชี)
    # ------------------------------------------------------------------
    def _od19_reconcile_account_lines(self, account_id, partner_id=None):
        """Reconcile every posted, unreconciled journal item of ``account_id``.

        Used by the advance / cheque / petty-cash / expense flows so the
        custom journal entries are really matched against the related
        invoice or payment lines instead of leaving an open residual.

        :param account_id: id of the account whose lines must be matched
        :param partner_id: optional partner to restrict the match to
        :return: ``True`` when lines were reconciled, ``False`` otherwise
        """
        self.ensure_one()
        account = self.env["account.account"].browse(account_id)
        if not account or not (
            account.reconcile
            or account.account_type in ("asset_cash", "liability_credit_card")
        ):
            return False
        domain = [
            ("company_id", "=", self.company_id.id),
            ("account_id", "=", account.id),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
        ]
        if partner_id:
            domain.append(("partner_id", "=", partner_id))
        lines = self.env["account.move.line"].search(domain)
        return self._od19_reconcile_move_lines(lines)

    @api.model
    def _od19_reconcile_move_lines(self, lines):
        """Reconcile an explicit set of journal items.

        Unlike :meth:`_od19_reconcile_account_lines`, which searches every
        open line of an account, this helper only matches the given lines.
        Use it when several unrelated documents share the same account and
        partner (credit notes, staged payments, ...) and the match must stay
        scoped to one document pair.

        :param lines: ``account.move.line`` recordset
        :return: ``True`` when the lines were reconciled, ``False`` otherwise
        """
        lines = lines.filtered(
            lambda line: line.parent_state == "posted" and not line.reconciled
        )
        if len(lines) < 2:
            return False
        lines.reconcile()
        return True
