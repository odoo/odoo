# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models

from .account_payment import PREPARE_STATE_SELECTION


class AccountMove(models.Model):
    _inherit = "account.move"

    # ------------------------------------------------------------------
    # Retrospective look-up: from a posted bill / invoice back to every
    # payment voucher that was prepared for it, even after the bill has
    # been fully reconciled and can no longer be edited.
    # ------------------------------------------------------------------
    od19_payment_ids = fields.Many2many(
        comodel_name="account.payment",
        string="ใบสำคัญจ่าย/รับ / Payment vouchers",
        compute="_compute_od19_payment_ids",
        search="_search_od19_payment_ids",
        help="รายการจ่ายที่ชำระ/เตรียมชำระเอกสารนี้ รวมรายการที่พักไว้รอตัดจ่าย",
    )
    od19_voucher_count = fields.Integer(
        string="จำนวนใบสำคัญ / Voucher count",
        compute="_compute_od19_voucher_count",
    )
    od19_voucher_summary = fields.Text(
        string="ประวัติใบสำคัญ / Voucher history",
        compute="_compute_od19_voucher_summary",
        help="สรุปเลขที่ใบสำคัญ สถานะการจัดทำ/อนุมัติ และสถานะการจ่าย "
        "สำหรับแสดงบนใบตั้งหนี้เพื่อการตรวจสอบย้อนหลัง",
    )

    @api.depends(
        "matched_payment_ids",
        "line_ids.matched_debit_ids",
        "line_ids.matched_credit_ids",
    )
    def _compute_od19_payment_ids(self):
        Payment = self.env["account.payment"]
        has_staging = "od19_pending_reconcile_line_ids" in Payment._fields
        for move in self:
            payments = move.matched_payment_ids
            # Unsaved moves carry a NewId and cannot have staged payments yet.
            if has_staging and isinstance(move.id, int):
                payments |= Payment.search(
                    [("od19_pending_reconcile_line_ids.move_id", "=", move.id)]
                )
            move.od19_payment_ids = payments

    def _search_od19_payment_ids(self, operator, value):
        """Make ``od19_payment_ids`` searchable (needed as a compute dependency).

        The field unions reconciled payments with payments whose source lines
        are still staged, so the domain is resolved through the payments'
        own ``od19_source_move_ids`` and translated back to move ids.
        """
        payments = self.env["account.payment"].search([("id", operator, value)])
        move_ids = payments.od19_source_move_ids.ids
        if operator in ("!=", "not in"):
            return [("id", "not in", move_ids)]
        return [("id", "in", move_ids)]

    @api.depends("od19_payment_ids")
    def _compute_od19_voucher_count(self):
        for move in self:
            move.od19_voucher_count = len(move.od19_payment_ids)

    @api.depends("od19_payment_ids", "od19_payment_ids.od19_prepare_state")
    def _compute_od19_voucher_summary(self):
        prepare_labels = dict(PREPARE_STATE_SELECTION)
        for move in self:
            lines = []
            for payment in move.od19_payment_ids.sorted("id"):
                number = payment.od19_voucher_no or payment.name or "-"
                prepare_state = prepare_labels.get(
                    payment.od19_prepare_state, payment.od19_prepare_state or ""
                )
                lines.append(f"{number} · {prepare_state} · {payment.state}")
            move.od19_voucher_summary = "\n".join(lines)

    def action_od19_open_vouchers(self):
        """Open the vouchers linked to this document (back-link button)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบสำคัญจ่าย/รับ / Payment Vouchers"),
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("id", "in", self.od19_payment_ids.ids)],
            "context": {"create": False},
        }
