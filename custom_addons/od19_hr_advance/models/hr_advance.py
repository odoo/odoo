# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Od19HrAdvance(models.Model):
    """ใบเบิกเงินทดรองจ่ายพนักงาน (Employee cash advance).

    Unlike ``hr.expense`` (a reimbursement of money the employee already
    spent) an advance is money the company gives *before* spending. The
    amount therefore sits on a dedicated employee receivable account until
    it is cleared, and any unused balance has to be returned.
    """

    _name = "od19.hr.advance"
    _description = "Employee Advance"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _order = "date desc, id desc"

    # OCA tier validation: submitting an advance always goes through the two
    # tiers defined in data/tier_definition_data.xml (supervisor then
    # accounting) before it can be approved and paid.
    _state_field = "state"
    _state_from = ["draft", "waiting_approval"]
    _state_to = ["approved"]
    _cancel_state = "cancel"
    _tier_validation_manual_config = False

    name = fields.Char(
        string="Number",
        default="/",
        readonly=True,
        copy=False,
        index=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Employee Contact",
        compute="_compute_partner_id",
        store=True,
        readonly=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        related="employee_id.department_id",
        store=True,
        readonly=True,
    )
    date = fields.Date(
        string="Request Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    purpose = fields.Char(string="Purpose", tracking=True)
    advance_account_id = fields.Many2one(
        "account.account",
        string="Employee Advance Account",
        required=True,
        tracking=True,
        help="บัญชีลูกหนี้พนักงาน/เงินทดรองจ่าย ที่ใช้ติดตามยอดคงค้างจนกว่าจะเคลียร์ครบ",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Payment Journal",
        domain="[('type', 'in', ('bank', 'cash'))]",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("waiting_approval", "Waiting Approval"),
            ("approved", "Approved"),
            ("paid", "Paid"),
            ("cleared", "Cleared"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        copy=False,
    )

    payment_id = fields.Many2one(
        "account.payment", string="Payment", readonly=True, copy=False
    )
    payment_date = fields.Date(
        string="Payment Date", readonly=True, copy=False, tracking=True
    )
    clear_move_id = fields.Many2one(
        "account.move", string="Clearing Entry", readonly=True, copy=False
    )
    clear_date = fields.Date(
        string="Clearing Date", readonly=True, copy=False, tracking=True
    )
    cleared_amount = fields.Monetary(
        string="Cleared Amount",
        currency_field="currency_id",
        compute="_compute_cleared_amount",
        store=True,
    )
    remaining_amount = fields.Monetary(
        string="Remaining Amount",
        currency_field="currency_id",
        compute="_compute_remaining_amount",
        store=True,
    )
    hr_expense_ids = fields.One2many(
        "hr.expense",
        "od19_hr_advance_id",
        string="Cleared Expenses",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    note = fields.Text(string="Notes")

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("employee_id", "employee_id.work_contact_id")
    def _compute_partner_id(self):
        for advance in self:
            employee = advance.employee_id
            advance.partner_id = (
                employee.work_contact_id or employee.user_id.partner_id
            )

    @api.depends(
        "amount",
        "advance_account_id",
        "payment_id.move_id.line_ids.amount_residual",
        "payment_id.move_id.line_ids.account_id",
    )
    def _compute_cleared_amount(self):
        """ยอดที่เคลียร์แล้ว = ยอดเบิก - ยอดคงเหลือในบัญชีลูกหนี้พนักงาน."""
        for advance in self:
            residual = 0.0
            move = advance.payment_id.move_id
            if move and advance.advance_account_id:
                advance_lines = move.line_ids.filtered(
                    lambda line: line.account_id == advance.advance_account_id
                )
                residual = sum(abs(line.amount_residual) for line in advance_lines)
            advance.cleared_amount = (
                advance.amount - residual if advance.amount else 0.0
            )

    @api.depends("amount", "cleared_amount")
    def _compute_remaining_amount(self):
        for advance in self:
            advance.remaining_amount = advance.amount - advance.cleared_amount

    # ------------------------------------------------------------------
    # Constraints / create
    # ------------------------------------------------------------------
    @api.constrains("amount")
    def _check_amount(self):
        for advance in self:
            if advance.amount <= 0:
                raise ValidationError(
                    _("Advance amount must be greater than zero.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("od19.hr.advance") or "/"
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_confirm(self):
        """ส่งคำขออนุมัติ (ผ่านสายอนุมัติขั้นบันได 2 ชั้น).

        ถ้ายอดต้องอนุมัติ คำขอจะถูกย้ายไปสถานะ ``waiting_approval`` และสร้าง
        คำขออนุมัติ เมื่ออนุมัติครบทุกชั้นแล้วกดยืนยันอีกครั้งจึงจะไปสถานะ
        ``approved`` และพร้อมจ่ายเงิน
        """
        awaiting = self.browse()
        for advance in self:
            if advance.state not in ("draft", "waiting_approval"):
                raise UserError(
                    _("Only draft advances can be submitted for approval.")
                )
            if not advance.employee_id:
                raise UserError(_("Please select an employee."))
            if not advance.advance_account_id:
                raise UserError(
                    _("Please select the employee advance account.")
                )
            # ``need_validation`` เป็น computed แบบไม่เก็บค่า จึงอาจค้างค่าเดิม
            # ที่ cache ไว้ก่อนสร้างคำขออนุมัติ ให้ล้างก่อนตรวจสอบ
            advance.invalidate_recordset(["need_validation"])
            if advance.review_ids:
                if advance.validation_status != "validated":
                    raise UserError(
                        _(
                            "This advance is waiting for tier validation before "
                            "it can be approved."
                        )
                    )
            elif advance.need_validation:
                awaiting |= advance
        if awaiting:
            awaiting.write({"state": "waiting_approval"})
            awaiting.request_validation()
        for advance in self - awaiting:
            if advance.state != "approved":
                advance.state = "approved"
        return True

    def _od19_get_payment_journal(self):
        self.ensure_one()
        if self.journal_id:
            return self.journal_id
        Journal = self.env["account.journal"].with_company(self.company_id)
        journal = Journal.search(
            Journal._check_company_domain(self.company_id)
            + [("type", "in", ("bank", "cash"))],
            limit=1,
        )
        if not journal:
            raise UserError(
                _("Please configure a bank or cash journal to pay this advance.")
            )
        return journal

    def _od19_get_payment_method_line(self, journal):
        """เลือก outbound payment method line ที่มีบัญชีค้างจ่ายครบถ้วน.

        ถ้า journal ที่สร้างเองไม่มี ``payment_account_id`` จะผูกบัญชีค้างจ่าย
        ของบริษัทให้อัตโนมัติ มิฉะนั้น Odoo จะสร้างรายการบัญชีไม่ได้
        """
        self.ensure_one()
        lines = journal.outbound_payment_method_line_ids
        if not lines:
            raise UserError(
                _("The journal %s has no outbound payment method configured.")
                % journal.display_name
            )
        method_line = lines.filtered("payment_account_id")[:1] or lines[:1]
        if not method_line.payment_account_id:
            outstanding = (
                self.env["account.chart.template"]
                .with_company(self.company_id)
                .ref(
                    "account_journal_payment_credit_account_id",
                    raise_if_not_found=False,
                )
                or self.company_id.transfer_account_id
            )
            if not outstanding:
                raise UserError(
                    _(
                        "No outstanding payments account is configured for the "
                        "journal %s."
                    )
                    % journal.display_name
                )
            method_line.payment_account_id = outstanding
        return method_line

    def action_pay(self):
        """จ่ายเงินทดรองให้พนักงานด้วย ``account.payment`` จริง.

        เดบิตบัญชีลูกหนี้พนักงาน (``advance_account_id``) เครดิตบัญชีเงินสด/ธนาคาร
        เพื่อให้ยอดคงค้างถูกติดตามจนกว่าจะเคลียร์
        """
        for advance in self:
            if advance.state != "approved":
                raise UserError(_("Only approved advances can be paid."))
            if not advance.partner_id:
                raise UserError(
                    _(
                        "No contact is linked to the employee %s, please "
                        "configure one."
                    )
                    % advance.employee_id.name
                )
            if not advance.advance_account_id:
                raise UserError(_("Please select the employee advance account."))
            journal = advance._od19_get_payment_journal()
            method_line = advance._od19_get_payment_method_line(journal)
            date = advance.payment_date or fields.Date.context_today(advance)
            payment = self.env["account.payment"].create(
                {
                    "payment_type": "outbound",
                    "partner_type": "supplier",
                    "partner_id": advance.partner_id.id,
                    "amount": advance.amount,
                    "currency_id": advance.currency_id.id,
                    "date": date,
                    "journal_id": journal.id,
                    "payment_method_line_id": method_line.id,
                    "destination_account_id": advance.advance_account_id.id,
                    "memo": advance.name,
                    # เงินทดรองให้พนักงานไม่ใช่การจ่ายชำระเจ้าหนี้ จึงไม่ต้องมี
                    # Vendor Bill ก่อน (ข้ามกติกา AP bill-first)
                    "od19_is_expense_payment": True,
                }
            )
            payment.action_post()
            advance.write(
                {
                    "payment_id": payment.id,
                    "payment_date": date,
                    "journal_id": journal.id,
                    "state": "paid",
                }
            )
            advance.invalidate_recordset(["cleared_amount", "remaining_amount"])
        return True

    def action_open_clear_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Clear Advance"),
            "res_model": "od19.hr.advance.clear",
            "view_mode": "form",
            "target": "new",
            "context": {"default_advance_id": self.id},
        }

    def action_cancel(self):
        for advance in self:
            if advance.state in ("paid", "cleared"):
                raise UserError(
                    _("Paid or cleared advances cannot be cancelled.")
                )
            advance.state = "cancel"
        return True

    def action_draft(self):
        for advance in self:
            if advance.state != "cancel":
                raise UserError(
                    _("Only cancelled advances can be reset to draft.")
                )
            advance.state = "draft"
        return True
