from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class Od19DoubtfulDebtWriteoff(models.Model):
    _name = "od19.doubtful.debt.writeoff"
    _description = "Bad Debt Write-off"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(default="New", copy=False, required=True)
    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    journal_id = fields.Many2one(
        "account.journal",
        required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
    )
    expense_account_id = fields.Many2one(
        "account.account",
        string="Bad Debt Expense",
        required=True,
        domain="[('account_type', '=', 'expense')]",
    )
    partner_id = fields.Many2one("res.partner", required=True, tracking=True)
    reason = fields.Text(
        required=True,
        help="เหตุผลการตัดหนี้สูญ (เช่น ลูกหนี้เลิกกิจการ, ค้นหาตัวไม่พบ)",
    )
    reference = fields.Char(
        help="เอกสารอ้างอิง/หลักฐานประกอบ (เช่น ฎ.186 (2534), ม.65 ทวิ (9))",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    approver_id = fields.Many2one("res.users", readonly=True, copy=False)
    approval_date = fields.Date(readonly=True, copy=False)
    line_ids = fields.One2many(
        "od19.doubtful.debt.writeoff.line",
        "writeoff_id",
        string="Written-off Receivables",
        copy=True,
    )
    move_id = fields.Many2one("account.move", readonly=True, copy=False)
    note = fields.Text()
    total_amount = fields.Monetary(
        compute="_compute_total_amount",
        store=True,
        string="Total Write-off",
    )
    evidence_count = fields.Integer(
        compute="_compute_evidence_count",
        string="Evidence",
    )

    @api.depends("line_ids.amount")
    def _compute_total_amount(self):
        for writeoff in self:
            writeoff.total_amount = sum(writeoff.line_ids.mapped("amount"))

    def _compute_evidence_count(self):
        for writeoff in self:
            writeoff.evidence_count = self.env["ir.attachment"].search_count(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", writeoff.id),
                ]
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "od19.doubtful.debt.writeoff"
                    )
                    or "New"
                )
        return super().create(vals_list)

    @api.constrains("line_ids")
    def _check_lines_partner(self):
        for writeoff in self:
            wrong = writeoff.line_ids.filtered(
                lambda line: line.move_line_id.partner_id != writeoff.partner_id
            )
            if wrong:
                raise ValidationError(
                    "รายการตัดหนี้สูญต้องเป็นลูกหนี้ของ %s เท่านั้น"
                    % writeoff.partner_id.display_name
                )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_approve(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError("อนุมัติได้เฉพาะเอกสารสถานะร่างเท่านั้น")
        if not self.env.user.has_group("account.group_account_manager"):
            raise UserError("เฉพาะผู้จัดการบัญชี (Account Manager) เท่านั้นที่อนุมัติได้")
        self.write(
            {
                "state": "approved",
                "approver_id": self.env.user.id,
                "approval_date": fields.Date.context_today(self),
            }
        )
        return True

    def action_post(self):
        for writeoff in self:
            if writeoff.state != "approved":
                raise UserError("ต้องได้รับการอนุมัติก่อนจึงจะตัดหนี้สูญได้")
            if not writeoff.line_ids:
                raise UserError("ไม่มีรายการลูกหนี้ที่จะตัดหนี้สูญ")
            if writeoff.evidence_count <= 0:
                raise UserError("ต้องแนบหลักฐานประกอบการตัดหนี้สูญก่อนลงบัญชี")
            total = writeoff.total_amount
            if writeoff.currency_id.is_zero(total):
                raise UserError("ยอดตัดหนี้สูญเป็นศูนย์ ไม่สามารถลงบัญชีได้")
            move = writeoff._od19_create_move(total)
            ar_lines = writeoff.line_ids.move_line_id
            writeoff._od19_reconcile(move, ar_lines)
            writeoff.write({"move_id": move.id, "state": "posted"})
        return True

    def _od19_create_move(self, total):
        self.ensure_one()
        ar_account = self.partner_id.property_account_receivable_id
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": self.date,
                "journal_id": self.journal_id.id,
                "ref": self.name,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": self.expense_account_id.id,
                            "name": self.name,
                            "partner_id": self.partner_id.id,
                            "debit": total,
                            "credit": 0.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": ar_account.id,
                            "name": self.name,
                            "partner_id": self.partner_id.id,
                            "debit": 0.0,
                            "credit": total,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def _od19_reconcile(self, move, ar_lines):
        self.ensure_one()
        ar_account = self.partner_id.property_account_receivable_id
        counterpart = move.line_ids.filtered(
            lambda line: line.account_id == ar_account
        )
        (counterpart | ar_lines).reconcile()

    def action_cancel(self):
        for writeoff in self:
            if writeoff.state not in ("draft", "approved"):
                raise UserError("ยกเลิกได้เฉพาะเอกสารที่ยังไม่ลงบัญชีเท่านั้น")
            writeoff.state = "cancelled"
        return True

    def action_draft(self):
        for writeoff in self:
            if writeoff.state != "cancelled":
                raise UserError("ตั้งกลับเป็นร่างได้เฉพาะเอกสารที่ยกเลิกแล้วเท่านั้น")
            writeoff.write(
                {
                    "state": "draft",
                    "approver_id": False,
                    "approval_date": False,
                }
            )
        return True

    def action_view_move(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
            "target": "current",
        }


class Od19DoubtfulDebtWriteoffLine(models.Model):
    _name = "od19.doubtful.debt.writeoff.line"
    _description = "Bad Debt Write-off Line"

    writeoff_id = fields.Many2one(
        "od19.doubtful.debt.writeoff",
        required=True,
        ondelete="cascade",
    )
    move_line_id = fields.Many2one(
        "account.move.line",
        string="Receivable Line",
        required=True,
        ondelete="restrict",
    )
    amount = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(related="writeoff_id.currency_id")
    date = fields.Date(related="move_line_id.date")
    date_maturity = fields.Date(related="move_line_id.date_maturity")
    account_id = fields.Many2one(related="move_line_id.account_id")
    move_name = fields.Char(related="move_line_id.move_name")
