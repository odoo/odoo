from odoo import api, fields, models
from odoo.exceptions import UserError


class Od19DoubtfulDebtWriteoffWizard(models.TransientModel):
    _name = "od19.doubtful.debt.writeoff.wizard"
    _description = "Bad Debt Write-off Wizard"

    partner_id = fields.Many2one("res.partner", required=True)
    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
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
    reason = fields.Text(required=True)
    reference = fields.Char()
    line_ids = fields.One2many(
        "od19.doubtful.debt.writeoff.wizard.line",
        "wizard_id",
        string="Receivables to Write Off",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        company = self.env.company
        res.setdefault("company_id", company.id)
        res.setdefault(
            "journal_id", company.od19_doubtful_debt_journal_id.id
        )
        res.setdefault(
            "expense_account_id",
            company.od19_doubtful_debt_expense_account_id.id,
        )
        return res

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for wizard in self:
            wizard.line_ids = False
            if not wizard.partner_id:
                continue
            lines = self.env["account.move.line"].search(
                [
                    ("partner_id", "=", wizard.partner_id.id),
                    ("account_id.account_type", "=", "asset_receivable"),
                    ("parent_state", "=", "posted"),
                    ("reconciled", "=", False),
                    ("company_id", "=", wizard.company_id.id),
                ]
            )
            wizard.line_ids = [
                (
                    0,
                    0,
                    {
                        "move_line_id": line.id,
                        "amount": line.amount_residual,
                    },
                )
                for line in lines
            ]

    def action_create_writeoff(self):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda line: line.move_line_id)
        if not lines:
            raise UserError("ไม่มีรายการลูกหนี้ที่จะตัดหนี้สูญ")
        writeoff = self.env["od19.doubtful.debt.writeoff"].create(
            {
                "partner_id": self.partner_id.id,
                "date": self.date,
                "company_id": self.company_id.id,
                "journal_id": self.journal_id.id,
                "expense_account_id": self.expense_account_id.id,
                "reason": self.reason,
                "reference": self.reference,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "move_line_id": line.move_line_id.id,
                            "amount": line.amount,
                        },
                    )
                    for line in lines
                ],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "od19.doubtful.debt.writeoff",
            "res_id": writeoff.id,
            "view_mode": "form",
            "target": "current",
        }


class Od19DoubtfulDebtWriteoffWizardLine(models.TransientModel):
    _name = "od19.doubtful.debt.writeoff.wizard.line"
    _description = "Bad Debt Write-off Wizard Line"

    wizard_id = fields.Many2one(
        "od19.doubtful.debt.writeoff.wizard",
        required=True,
        ondelete="cascade",
    )
    move_line_id = fields.Many2one(
        "account.move.line",
        string="Receivable Line",
        required=True,
    )
    amount = fields.Monetary(
        compute="_compute_amount",
        store=True,
        readonly=False,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    date = fields.Date(related="move_line_id.date")
    date_maturity = fields.Date(related="move_line_id.date_maturity")

    @api.depends("move_line_id")
    def _compute_amount(self):
        for line in self:
            line.amount = line.move_line_id.amount_residual
