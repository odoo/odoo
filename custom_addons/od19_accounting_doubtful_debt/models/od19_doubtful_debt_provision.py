from odoo import api, fields, models
from odoo.exceptions import UserError


class Od19DoubtfulDebtProvision(models.Model):
    _name = "od19.doubtful.debt.provision"
    _description = "Doubtful Debt Provision"
    _inherit = ["mail.thread"]
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
        string="Doubtful Debt Expense",
        required=True,
        domain="[('account_type', '=', 'expense')]",
    )
    allowance_account_id = fields.Many2one(
        "account.account",
        string="Doubtful Debt Allowance",
        required=True,
        domain="[('account_type', 'in', ('asset_current', 'asset_non_current'))]",
        help="บัญชีปรับมูลค่าลูกหนี้ (ค่าเผื่อหนี้สงสัยจะสูญ)",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    line_ids = fields.One2many(
        "od19.doubtful.debt.provision.line",
        "provision_id",
        string="Provision Lines",
        copy=True,
    )
    move_id = fields.Many2one("account.move", readonly=True, copy=False)
    note = fields.Text()
    total_balance = fields.Monetary(
        compute="_compute_totals",
        store=True,
        string="Total Open AR",
    )
    total_provision_amount = fields.Monetary(
        compute="_compute_totals",
        store=True,
        string="Total Provision",
    )

    @api.depends("line_ids.balance", "line_ids.provision_amount")
    def _compute_totals(self):
        for provision in self:
            provision.total_balance = sum(provision.line_ids.mapped("balance"))
            provision.total_provision_amount = sum(
                provision.line_ids.mapped("provision_amount")
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "od19.doubtful.debt.provision"
                    )
                    or "New"
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Compute helpers
    # ------------------------------------------------------------------
    def _od19_age_days(self, move_line):
        """Age of an open receivable line in days at the provision date."""
        self.ensure_one()
        reference = move_line.date_maturity or move_line.date
        return (self.date - reference).days

    def _od19_open_receivable_lines(self):
        self.ensure_one()
        return self.env["account.move.line"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("account_id.account_type", "=", "asset_receivable"),
                ("parent_state", "=", "posted"),
                ("reconciled", "=", False),
            ]
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_compute(self):
        """(Re)build the provision lines from the current open receivables."""
        for provision in self:
            if provision.state != "draft":
                raise UserError("คำนวณได้เฉพาะเอกสารสถานะร่างเท่านั้น")
            buckets = provision.company_id.od19_doubtful_debt_aging_line_ids
            if not buckets:
                raise UserError(
                    "ยังไม่ได้ตั้งค่าช่วงอายุหนี้ (aging bucket) สำหรับบริษัทนี้"
                )
            provision.line_ids.unlink()
            grouped = {}
            for move_line in provision._od19_open_receivable_lines():
                if not move_line.partner_id:
                    continue
                previous = move_line.amount_residual
                if provision.currency_id.is_zero(previous):
                    continue
                days = provision._od19_age_days(move_line)
                bucket = buckets.filtered(lambda b: b._od19_match(days))[:1]
                if not bucket:
                    continue
                key = (move_line.partner_id.id, bucket.id)
                grouped[key] = grouped.get(key, 0.0) + previous
            commands = []
            for (partner_id, bucket_id), balance in grouped.items():
                bucket = buckets.browse(bucket_id)
                commands.append(
                    (
                        0,
                        0,
                        {
                            "partner_id": partner_id,
                            "aging_line_id": bucket_id,
                            "balance": balance,
                            "provision_rate": bucket.provision_rate,
                            "provision_amount": balance
                            * bucket.provision_rate
                            / 100.0,
                        },
                    )
                )
            provision.line_ids = commands
        return True

    def action_post(self):
        for provision in self:
            if provision.state != "draft":
                raise UserError("ลงบัญชีได้เฉพาะเอกสารสถานะร่างเท่านั้น")
            if not provision.line_ids:
                raise UserError("ไม่มีรายการตั้งค่าเผื่อ กรุณาคำนวณก่อนลงบัญชี")
            total = provision.total_provision_amount
            if provision.currency_id.is_zero(total):
                raise UserError("ยอดตั้งค่าเผื่อเป็นศูนย์ ไม่สามารถลงบัญชีได้")
            move = provision._od19_create_move(total)
            provision.write({"move_id": move.id, "state": "posted"})
        return True

    def _od19_create_move(self, total):
        self.ensure_one()
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
                            "debit": total,
                            "credit": 0.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": self.allowance_account_id.id,
                            "name": self.name,
                            "debit": 0.0,
                            "credit": total,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def action_cancel(self):
        for provision in self:
            if provision.state != "draft":
                raise UserError("ยกเลิกได้เฉพาะเอกสารสถานะร่างเท่านั้น")
            provision.state = "cancelled"
        return True

    def action_draft(self):
        for provision in self:
            if provision.state != "cancelled":
                raise UserError("ตั้งกลับเป็นร่างได้เฉพาะเอกสารที่ยกเลิกแล้วเท่านั้น")
            provision.state = "draft"
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


class Od19DoubtfulDebtProvisionLine(models.Model):
    _name = "od19.doubtful.debt.provision.line"
    _description = "Doubtful Debt Provision Line"

    provision_id = fields.Many2one(
        "od19.doubtful.debt.provision",
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one("res.partner", required=True)
    aging_line_id = fields.Many2one(
        "od19.doubtful.debt.aging.line",
        string="Aging Bucket",
        required=True,
    )
    balance = fields.Monetary(currency_field="currency_id")
    provision_rate = fields.Float(string="Rate (%)", digits=(5, 2))
    provision_amount = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(related="provision_id.currency_id")
    company_id = fields.Many2one(related="provision_id.company_id")
