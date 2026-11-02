# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class Od19AccountPeriodClearLine(models.TransientModel):
    _name = "od19.account.period.clear.line"
    _description = "Period Clearing Open Item"

    wizard_id = fields.Many2one(
        comodel_name="od19.account.period.clear.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="wizard_id.currency_id",
        string="Currency",
    )
    line_count = fields.Integer(string="Open Items", readonly=True)
    debit = fields.Monetary(
        string="Debit", currency_field="currency_id", readonly=True
    )
    credit = fields.Monetary(
        string="Credit", currency_field="currency_id", readonly=True
    )
    balance = fields.Monetary(
        string="Balance", currency_field="currency_id", readonly=True
    )


class Od19AccountPeriodClearWizard(models.TransientModel):
    """Period-end clearing (กระทบยอดปิดงวด).

    Lists the still-open journal items of the control accounts of a period
    (AR/AP, bank, suspense, VAT/WHT control accounts, ...) grouped by account
    and partner, and lets the accountant clear them in one action. The match
    itself is delegated to the central helper
    ``account.move._od19_reconcile_move_lines`` so every custom flow
    (advance / cheque / petty cash / expense) reconciles the same way.
    """

    _name = "od19.account.period.clear.wizard"
    _description = "Period Clearing Reconciliation Wizard"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Currency",
    )
    date_from = fields.Date(
        string="Date From",
        required=True,
        default=lambda self: self._default_date_from(),
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    account_ids = fields.Many2many(
        comodel_name="account.account",
        string="Control Accounts",
        domain="['|', ('reconcile', '=', True),"
        " ('account_type', 'in', ('asset_cash', 'liability_credit_card'))]",
        default=lambda self: self._od19_eligible_accounts(),
        help="Accounts whose open journal items must be cleared at period "
        "close. Leave empty to scan every eligible account.",
    )
    line_ids = fields.One2many(
        comodel_name="od19.account.period.clear.line",
        inverse_name="wizard_id",
        string="Open Items",
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Defaults / helpers
    # ------------------------------------------------------------------
    @api.model
    def _default_date_from(self):
        today = fields.Date.context_today(self)
        return today.replace(day=1)

    @api.model
    def _od19_eligible_accounts(self, company=None):
        """Accounts that Odoo is allowed to reconcile."""
        company = company or self.env.company
        return self.env["account.account"].search(
            [
                ("company_ids", "in", company.id),
                "|",
                ("reconcile", "=", True),
                ("account_type", "in", ("asset_cash", "liability_credit_card")),
            ]
        )

    def _od19_target_accounts(self):
        self.ensure_one()
        if self.account_ids:
            return self.account_ids
        return self._od19_eligible_accounts(self.company_id)

    def _od19_open_lines_domain(self, account_id=None, partner_id=None):
        """Open (unreconciled, posted) lines of the period."""
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
        ]
        if account_id:
            domain.append(("account_id", "=", account_id))
        else:
            targets = self._od19_target_accounts()
            domain.append(("account_id", "in", targets.ids))
        if partner_id:
            domain.append(("partner_id", "=", partner_id))
        return domain

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_load(self):
        """(Re)load the open items grouped by account and partner."""
        self.ensure_one()
        self.line_ids.unlink()
        account_move_line = self.env["account.move.line"]
        groups = {}
        for line in account_move_line.search(self._od19_open_lines_domain()):
            key = (line.account_id.id, line.partner_id.id)
            groups.setdefault(key, account_move_line)
            groups[key] |= line
        vals_list = [
            {
                "wizard_id": self.id,
                "account_id": account_id,
                "partner_id": partner_id,
                "line_count": len(group),
                "debit": sum(group.mapped("debit")),
                "credit": sum(group.mapped("credit")),
                "balance": sum(group.mapped("balance")),
            }
            for (account_id, partner_id), group in groups.items()
        ]
        if vals_list:
            self.env["od19.account.period.clear.line"].create(vals_list)
        return self._reload_action()

    def action_reconcile(self):
        """Reconcile every open item of the selected accounts for the period."""
        self.ensure_one()
        account_move_line = self.env["account.move.line"]
        reconcile = self.env["account.move"]._od19_reconcile_move_lines
        for line in self.line_ids:
            reconcile(
                account_move_line.search(
                    self._od19_open_lines_domain(
                        line.account_id.id, line.partner_id.id or None
                    )
                )
            )
        return self.action_load()

    def _reload_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Period Clearing"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
