from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountSpreadInvoiceWizard(models.TransientModel):
    _name = "account.spread.invoice.wizard"
    _description = "Create Spread from Invoice Line"

    move_line_id = fields.Many2one("account.move.line", required=True, readonly=True)
    estimated_amount = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )
    account_id = fields.Many2one("account.account", required=True, check_company=True)
    journal_id = fields.Many2one("account.journal", required=True, check_company=True)
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    period_type = fields.Selection(
        [("monthly", "Monthly"), ("quarterly", "Quarterly"), ("yearly", "Yearly")],
        required=True,
        default="monthly",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )

    def _default_deferred_account(self):
        company = self.env.company
        if "default_spread_revenue_account_id" in company._fields:
            return company.default_spread_revenue_account_id
        return False

    def _default_journal(self):
        return self.env["account.journal"].search(
            [("company_id", "=", self.env.company.id), ("type", "=", "general")],
            limit=1,
        )

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        move_line = self.env["account.move.line"].browse(res.get("move_line_id"))
        if move_line:
            res.setdefault("estimated_amount", abs(move_line.balance))
            base_date = move_line.move_id.invoice_date or move_line.move_id.date
            base_date = base_date or fields.Date.context_today(self)
            res.setdefault("date_start", base_date)
            res.setdefault("date_end", base_date + relativedelta(months=11, day=31))
            res.setdefault("company_id", move_line.company_id.id)
        default_account = self._default_deferred_account()
        if default_account:
            res.setdefault("account_id", default_account.id)
        default_journal = self._default_journal()
        if default_journal:
            res.setdefault("journal_id", default_journal.id)
        return res

    def action_create_spread(self):
        self.ensure_one()
        if self.estimated_amount <= 0:
            raise UserError(_("Estimated amount must be greater than zero."))

        spread_vals = {
            "name": self.move_line_id.name or _("Spread %s") % self.move_line_id.id,
            "account_id": self.account_id.id,
            "journal_id": self.journal_id.id,
            "company_id": self.company_id.id,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "period_type": self.period_type,
            "spread_type": (
                "sale"
                if self.move_line_id.move_id.move_type in ("out_invoice", "out_refund")
                else "purchase"
            ),
            "move_line_id": self.move_line_id.id,
            "estimated_amount": self.estimated_amount,
            "state": "draft",
        }
        spread = self.env["account.spread"].create(spread_vals)
        self.move_line_id.spread_id = spread.id
        spread.action_confirm()
        return {
            "type": "ir.actions.act_window",
            "name": _("Spread"),
            "res_model": "account.spread",
            "view_mode": "form",
            "res_id": spread.id,
            "target": "current",
        }
