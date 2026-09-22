from odoo import fields, models


class AccountBankAutoReconcileWizard(models.TransientModel):
    _name = "account.bank.auto.reconcile.wizard"
    _description = "Run auto-reconciliation on bank statement lines"
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
        required=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        required=True,
        check_company=True,
        domain="[('type', 'in', ('bank', 'cash', 'credit'))]",
    )
    from_date = fields.Date(
        string="From",
        required=True,
        default=lambda self: fields.Date.subtract(
            fields.Date.context_today(self), months=1
        ),
    )
    to_date = fields.Date(
        string="To",
        required=True,
        default=fields.Date.context_today,
    )

    def action_auto_reconcile(self):
        self.check_singleton()
        st_lines = self.env["account.bank.statement.line"].search(
            [
                ("journal_id", "=", self.journal_id.id),
                ("date", ">=", self.from_date),
                ("date", "<=", self.to_date),
                ("is_reconciled", "=", False),
                ("state", "!=", "cancel"),
            ]
        )
        # Deliberately not `_try_auto_reconcile_statement_lines` directly: that
        # one works on the whole recordset and one raising line aborts the lot.
        # `retire=False` because stamping `cron_last_check` is the CRON's
        # bookkeeping -- see the helper's docstring.
        st_lines._auto_reconcile_isolating_failures(
            company_id=self.company_id.id, retire=False
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": self.env._(
                    "Automatic reconciliation finished on %(count)s transactions.",
                    count=len(st_lines),
                ),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
