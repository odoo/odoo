# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

# Sequence code used to draw the Thai document number shown on the
# payment voucher / payment receipt, keyed by the Odoo payment direction.
VOUCHER_SEQUENCE_BY_PAYMENT_TYPE = {
    "outbound": "account.voucher.vendor.payment",
    "inbound": "account.voucher.customer.payment",
}

# Move types that a payment can settle and that carry untaxed / VAT totals.
SOURCE_BILL_MOVE_TYPES = ("in_invoice", "in_refund", "out_invoice", "out_refund")

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
    od19_approval_override = fields.Boolean(
        string="ข้ามการอนุมัติ / Approval Override",
        copy=False,
        readonly=True,
        tracking=True,
        help="ตั้งค่าเมื่อผู้อนุมัติสั่งข้ามขั้นอนุมัติ (กรณีเร่งด่วน) "
        "เพื่อให้ Post ได้โดยไม่ต้องผ่านการอนุมัติ",
    )
    od19_override_reason = fields.Text(
        string="เหตุผลการข้ามการอนุมัติ / Override reason",
        copy=False,
        tracking=True,
        help="เหตุผลบังคับที่ต้องกรอกก่อนกด \"ข้ามการอนุมัติ\" เพื่อเป็นหลักฐานตรวจสอบ",
    )
    od19_override_by = fields.Many2one(
        comodel_name="res.users",
        string="ผู้สั่งข้ามการอนุมัติ / Overridden by",
        copy=False,
        readonly=True,
        tracking=True,
    )

    # ------------------------------------------------------------------
    # Retrospective look-up helpers (register, back-link and reports).
    # Everything below is derived, never stored, so no ledger data is
    # duplicated on the payment.
    # ------------------------------------------------------------------
    od19_source_move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="od19_payment_source_move_rel",
        column1="payment_id",
        column2="move_id",
        string="เอกสารต้นทาง / Source documents",
        compute="_compute_od19_source_move_ids",
        help="ใบแจ้งหนี้/ใบตั้งหนี้ที่รายการจ่ายนี้ชำระ รวมรายการที่พักไว้ "
        "ตอนเตรียมจ่ายซึ่งยังไม่ถูกตัดจ่ายจนกว่าจะ Post",
    )
    od19_payee_display = fields.Char(
        string="จ่ายให้/รับจาก / Paid to",
        compute="_compute_od19_payee_display",
    )
    od19_direction_label = fields.Char(
        string="ทิศทาง / Direction",
        compute="_compute_od19_direction_label",
    )
    od19_bill_untaxed_amount = fields.Monetary(
        string="ยอดก่อนภาษี / Untaxed",
        currency_field="currency_id",
        compute="_compute_od19_bill_amounts",
    )
    od19_bill_tax_amount = fields.Monetary(
        string="ภาษีมูลค่าเพิ่ม / VAT",
        currency_field="currency_id",
        compute="_compute_od19_bill_amounts",
    )
    od19_bill_total_amount = fields.Monetary(
        string="ยอดรวมเอกสารต้นทาง / Source total",
        currency_field="currency_id",
        compute="_compute_od19_bill_amounts",
    )
    od19_due_date = fields.Date(
        string="วันครบกำหนด / Due date",
        compute="_compute_od19_source_info",
    )
    od19_source_reference = fields.Char(
        string="เอกสารอ้างอิง / Source reference",
        compute="_compute_od19_source_info",
    )
    od19_payment_term_name = fields.Char(
        string="เงื่อนไขชำระ / Payment terms",
        compute="_compute_od19_source_info",
    )
    od19_salesperson_id = fields.Many2one(
        comodel_name="res.users",
        string="พนักงานขาย / Salesperson",
        compute="_compute_od19_source_info",
    )
    od19_job_no = fields.Char(
        string="เลขที่งาน / Job No.",
        compute="_compute_od19_job_no",
    )
    # Cheque details are surfaced through guarded fields so the report does
    # not need a hard dependency on the cheque module.
    od19_cheque_number = fields.Char(
        string="เลขที่เช็ค / Cheque No.",
        compute="_compute_od19_cheque_info",
    )
    od19_cheque_bank = fields.Char(
        string="ธนาคาร / Bank",
        compute="_compute_od19_cheque_info",
    )
    od19_cheque_bank_branch = fields.Char(
        string="สาขา / Branch",
        compute="_compute_od19_cheque_info",
    )
    od19_cheque_date = fields.Date(
        string="วันที่เช็ค / Cheque date",
        compute="_compute_od19_cheque_info",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends(
        "od19_pending_reconcile_line_ids",
        "invoice_ids",
        "reconciled_invoice_ids",
        "reconciled_bill_ids",
    )
    def _compute_od19_source_move_ids(self):
        for payment in self:
            payment.od19_source_move_ids = (
                payment.od19_pending_reconcile_line_ids.move_id
                | payment.invoice_ids
                | payment.reconciled_invoice_ids
                | payment.reconciled_bill_ids
            )

    @api.depends("od19_payee_id", "partner_id")
    def _compute_od19_payee_display(self):
        for payment in self:
            payee = payment.od19_payee_id or payment.partner_id
            payment.od19_payee_display = payee.display_name or ""

    @api.depends("payment_type")
    def _compute_od19_direction_label(self):
        for payment in self:
            if payment.payment_type == "outbound":
                payment.od19_direction_label = _("จ่ายให้ / Paid to")
            else:
                payment.od19_direction_label = _("รับชำระจาก / Received from")

    @api.depends(
        "od19_pending_reconcile_line_ids",
        "invoice_ids",
        "reconciled_invoice_ids",
        "reconciled_bill_ids",
    )
    def _compute_od19_bill_amounts(self):
        for payment in self:
            bills = payment.od19_source_move_ids.filtered(
                lambda move: move.move_type in SOURCE_BILL_MOVE_TYPES
            )
            payment.od19_bill_untaxed_amount = sum(
                bills.mapped("amount_untaxed")
            )
            payment.od19_bill_tax_amount = sum(bills.mapped("amount_tax"))
            payment.od19_bill_total_amount = sum(bills.mapped("amount_total"))

    @api.depends(
        "od19_pending_reconcile_line_ids",
        "invoice_ids",
        "reconciled_invoice_ids",
        "reconciled_bill_ids",
    )
    def _compute_od19_source_info(self):
        for payment in self:
            moves = payment.od19_source_move_ids
            due_dates = [due for due in moves.mapped("invoice_date_due") if due]
            payment.od19_due_date = min(due_dates) if due_dates else False
            first_move = moves[:1]
            payment.od19_source_reference = first_move.invoice_origin or ""
            payment.od19_payment_term_name = (
                first_move.invoice_payment_term_id.name or ""
            )
            payment.od19_salesperson_id = first_move.invoice_user_id or False

    @api.depends(
        "od19_pending_reconcile_line_ids",
        "invoice_ids",
        "reconciled_invoice_ids",
        "reconciled_bill_ids",
    )
    def _compute_od19_job_no(self):
        for payment in self:
            payment.od19_job_no = payment._od19_find_job_no()

    def _od19_find_job_no(self):
        """Best-effort Job No. from the analytic account of the source bill.

        ``project.project`` is optional here: the report module must keep
        working on a database where the project modules are not installed.
        """
        self.ensure_one()
        if "project.project" not in self.env:
            return ""
        for line in self.od19_source_move_ids.line_ids:
            analytic_ids = [
                int(key)
                for key in (line.analytic_distribution or {})
                if str(key).isdigit()
            ]
            if not analytic_ids:
                continue
            project = self.env["project.project"].search(
                [("account_id", "in", analytic_ids)], limit=1
            )
            if project.job_no:
                return project.job_no
        return ""

    def _od19_get_source_bills(self):
        """Source invoices/bills only, for the voucher report line table."""
        self.ensure_one()
        return self.od19_source_move_ids.filtered(
            lambda move: move.move_type in SOURCE_BILL_MOVE_TYPES
        )

    def _od19_prepare_state_label(self):
        self.ensure_one()
        return dict(PREPARE_STATE_SELECTION).get(
            self.od19_prepare_state, self.od19_prepare_state or ""
        )

    def _od19_state_label(self):
        self.ensure_one()
        return dict(self._fields["state"].selection).get(self.state, self.state or "")

    def _compute_od19_cheque_info(self):
        """Cheque details, read through ``getattr`` to stay module-agnostic."""
        for payment in self:
            cheque = getattr(payment, "cheque_paid_id", False) or getattr(
                payment, "cheque_id", False
            )
            payment.od19_cheque_number = cheque.name or ""
            payment.od19_cheque_bank = cheque.bank_id.name or ""
            payment.od19_cheque_bank_branch = cheque.bank_branch or ""
            payment.od19_cheque_date = cheque.cheque_date or False

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

    def _od19_is_payment_approver(self):
        """Whether the current user may approve / override a payment."""
        return self.env.user.has_group(
            "od19_accounting_payment_voucher_reports.group_od19_payment_approver"
        ) or self.env.user.has_group("base.group_system")

    def _od19_can_bypass_sod(self):
        """Administrators may bypass the segregation-of-duties rule."""
        return self.env.user.has_group(
            "od19_accounting_payment_voucher_reports.group_od19_payment_admin"
        ) or self.env.user.has_group("base.group_system")

    def _od19_sod_blocks_approval(self):
        """True when SoD is enforced and the same user prepared and approves."""
        self.ensure_one()
        if not self.company_id.od19_enforce_prepare_sod:
            return False
        if not self.od19_prepared_by or self.od19_prepared_by != self.env.user:
            return False
        return not self._od19_can_bypass_sod()

    def action_od19_approve(self):
        """Approve step: record who approved the payment before it is paid."""
        for payment in self:
            if payment.od19_prepare_state != "prepared":
                raise UserError(_("ต้องเตรียมจ่ายก่อนจึงจะอนุมัติได้"))
            if payment._od19_sod_blocks_approval():
                raise UserError(
                    _(
                        "แยกหน้าที่ (Segregation of Duties): ผู้จัดทำไม่สามารถอนุมัติ "
                        "รายการที่ตนเองจัดทำได้\n\n"
                        "กรุณาให้ผู้อนุมัติท่านอื่นเป็นผู้กด \"อนุมัติ\" "
                        "(หรือผู้ดูแลระบบใช้ \"ข้ามการอนุมัติ\" พร้อมเหตุผล)"
                    )
                )
            payment.write(
                {
                    "od19_prepare_state": "approved",
                    "od19_approved_by": self.env.user.id,
                    "od19_approved_date": fields.Datetime.now(),
                }
            )
        return True

    def action_od19_override(self):
        """Emergency bypass of the approval step, with a mandatory reason.

        Only payment approvers (or administrators) may use it. The reason and
        the acting user are persisted so the override is fully auditable.
        """
        if not self._od19_is_payment_approver():
            raise UserError(
                _(
                    "เฉพาะผู้อนุมัติหรือผู้ดูแลระบบเท่านั้นที่ใช้ "
                    "\"ข้ามการอนุมัติ\" ได้"
                )
            )
        for payment in self:
            reason = (payment.od19_override_reason or "").strip()
            if not reason:
                raise UserError(
                    _("ต้องระบุเหตุผลการข้ามการอนุมัติก่อนจึงจะดำเนินการได้")
                )
            payment.write(
                {
                    "od19_approval_override": True,
                    "od19_override_by": self.env.user.id,
                }
            )
            payment.message_post(
                body=_(
                    "ข้ามการอนุมัติการจ่าย (Approval Override) โดย %(user)s — "
                    "เหตุผล: %(reason)s",
                    user=self.env.user.display_name,
                    reason=reason,
                )
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

    def _od19_requires_prepare_approval(self):
        """Return whether this payment must pass the Prepare -> Approve gate.

        Only vendor (outbound / supplier) disbursements are gated. Flows that
        create and post a payment in a single shot (HR expense reimbursement,
        automated / cross-module payments) are exempted here in one allow-list
        so the rule stays auditable instead of being scattered across callers.
        """
        self.ensure_one()
        if self.payment_type != "outbound" or self.partner_type != "supplier":
            return False
        if self.env.context.get("od19_skip_prepare_gate"):
            return False
        if "od19_is_expense_payment" in self._fields and self.od19_is_expense_payment:
            return False
        return True

    def _od19_check_prepare_approval(self):
        """Block posting when the Prepare -> Approve gate is enforced and unmet."""
        for payment in self:
            if not payment.company_id.od19_enforce_prepare_approval:
                continue
            if not payment._od19_requires_prepare_approval():
                continue
            if payment.od19_prepare_state == "approved":
                continue
            if payment.od19_approval_override:
                continue
            raise UserError(
                _(
                    "ยังไม่สามารถยืนยันรายการจ่ายได้ เนื่องจากยังไม่ผ่านการอนุมัติ\n\n"
                    "ขั้นตอนบังคับ: กด \"เตรียมจ่าย\" (Prepare) แล้ว "
                    "\"อนุมัติ\" (Approve) ก่อนจึงจะ Post ได้ "
                    "— หรือใช้ \"ข้ามการอนุมัติ\" พร้อมระบุเหตุผล (กรณีเร่งด่วน)\n\n"
                    "Payment %(name)s (คู่ค้า: %(partner)s) อยู่ในขั้น "
                    "\"%(state)s\"",
                    name=payment.name or payment.display_name,
                    partner=payment.partner_id.display_name or "-",
                    state=dict(PREPARE_STATE_SELECTION).get(
                        payment.od19_prepare_state, ""
                    ),
                )
            )

    def action_post(self):
        self._od19_check_prepare_approval()
        res = super().action_post()
        self._od19_assign_voucher_number()
        self._od19_reconcile_staged_lines()
        return res
