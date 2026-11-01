# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, _, fields, models
from odoo.exceptions import UserError

# Sequence code used to draw the Thai document number shown on the
# payment voucher / payment receipt, keyed by the Odoo payment direction.
VOUCHER_SEQUENCE_BY_PAYMENT_TYPE = {
    "outbound": "account.voucher.vendor.payment",
    "inbound": "account.voucher.customer.payment",
}

# Prepare -> Approve -> Pay. The number is drawn once at the "prepare" step so
# the voucher printed in draft already carries the final document number.
PREPARE_STATE_SELECTION = [
    ("draft", "ร่าง / Draft"),
    ("prepared", "เตรียมจ่าย / Prepared"),
    ("approved", "อนุมัติแล้ว / Approved"),
]


class AccountPayment(models.Model):
    _inherit = "account.payment"

    od19_voucher_no = fields.Char(
        string="เลขที่ใบสำคัญ / Voucher No.",
        copy=False,
        readonly=True,
        help="เลขที่ใบสำคัญจ่าย (PV) หรือใบสำคัญรับเงิน (RV) ที่รันจาก ir.sequence",
    )
    od19_prepare_state = fields.Selection(
        selection=PREPARE_STATE_SELECTION,
        string="ขั้นเตรียมจ่าย / Prepare Step",
        default="draft",
        copy=False,
        readonly=True,
        tracking=True,
        help="สถานะการเตรียมจ่าย: ร่าง -> เตรียมจ่าย -> อนุมัติแล้ว",
    )
    od19_prepared_by = fields.Many2one(
        comodel_name="res.users",
        string="ผู้จัดทำ / Prepared by",
        copy=False,
        readonly=True,
        tracking=True,
    )
    od19_prepared_date = fields.Datetime(
        string="วันที่จัดทำ / Prepared on",
        copy=False,
        readonly=True,
        tracking=True,
    )
    od19_approved_by = fields.Many2one(
        comodel_name="res.users",
        string="ผู้อนุมัติ / Approved by",
        copy=False,
        readonly=True,
        tracking=True,
    )
    od19_approved_date = fields.Datetime(
        string="วันที่อนุมัติ / Approved on",
        copy=False,
        readonly=True,
        tracking=True,
    )
    od19_pending_reconcile_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        relation="od19_payment_pending_reconcile_rel",
        column1="payment_id",
        column2="line_id",
        string="รายการตั้งหนี้ที่รอตัดจ่าย / Source lines to settle",
        copy=False,
        readonly=True,
        help="รายการของใบแจ้งหนี้/ใบตั้งหนี้ที่ถูกเก็บไว้ตอนสร้างรายการจ่ายแบบ "
        "เตรียมจ่าย จะถูกตัดจ่าย (reconcile) ให้อัตโนมัติเมื่อ Post",
    )

    def _od19_voucher_sequence_code(self):
        self.ensure_one()
        return VOUCHER_SEQUENCE_BY_PAYMENT_TYPE.get(self.payment_type)

    def _od19_assign_voucher_number(self):
        """Assign the Thai document number once, based on the payment direction."""
        for payment in self:
            if payment.od19_voucher_no:
                continue
            sequence_code = payment._od19_voucher_sequence_code()
            if not sequence_code:
                continue
            number = self.env["ir.sequence"].next_by_code(sequence_code)
            if number:
                payment.od19_voucher_no = number
        return True

    def action_od19_prepare(self):
        """Prepare step: draw the voucher number and record who prepared it.

        The journal entry is still not posted, so nothing hits the ledger yet,
        but the printed voucher already carries its final number.
        """
        for payment in self:
            if payment.state != "draft":
                raise UserError(
                    _("เตรียมจ่ายได้เฉพาะรายการที่เป็นร่าง (Draft) เท่านั้น")
                )
            payment._od19_assign_voucher_number()
            payment.write(
                {
                    "od19_prepare_state": "prepared",
                    "od19_prepared_by": self.env.user.id,
                    "od19_prepared_date": fields.Datetime.now(),
                }
            )
        return True

    def action_od19_approve(self):
        """Approve step: record who approved the payment before it is paid."""
        for payment in self:
            if payment.od19_prepare_state != "prepared":
                raise UserError(_("ต้องเตรียมจ่ายก่อนจึงจะอนุมัติได้"))
            payment.write(
                {
                    "od19_prepare_state": "approved",
                    "od19_approved_by": self.env.user.id,
                    "od19_approved_date": fields.Datetime.now(),
                }
            )
        return True

    def _od19_reconcile_staged_lines(self):
        """Settle the source invoice/bill lines once the payment is posted.

        Payments created through the "Prepare payment" option of the Register
        Payment wizard are kept in draft, so the standard wizard reconciliation
        cannot run at creation time. It is replayed here instead.
        """
        helper = self.env["account.move"]._od19_reconcile_move_lines
        for payment in self.filtered("od19_pending_reconcile_line_ids"):
            if not payment.move_id:
                continue
            domain = [
                ("parent_state", "=", "posted"),
                ("account_type", "in", payment._get_valid_payment_account_types()),
                ("reconciled", "=", False),
            ]
            payment_lines = payment.move_id.line_ids.filtered_domain(domain)
            staged_lines = payment.od19_pending_reconcile_line_ids.filtered_domain(domain)
            for account in payment_lines.account_id:
                helper(
                    (payment_lines + staged_lines).filtered_domain(
                        [("account_id", "=", account.id), ("reconciled", "=", False)]
                    )
                )
            staged_lines.move_id.matched_payment_ids = [Command.link(payment.id)]
        return True

    def action_post(self):
        res = super().action_post()
        self._od19_assign_voucher_number()
        self._od19_reconcile_staged_lines()
        return res
