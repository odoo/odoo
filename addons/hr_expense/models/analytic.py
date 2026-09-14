from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class AccountAnalyticApplicability(models.Model):
    _inherit = "account.analytic.applicability"
    _description = "Analytic Plan's Applicabilities"

    business_domain = fields.Selection(
        selection_add=[
            ("expense", "Expense"),
        ],
        ondelete={"expense": "cascade"},
    )

    @api.depends("business_domain")
    def _compute_display_account_prefix(self):
        super()._compute_display_account_prefix()
        for applicability in self.filtered(
            lambda rec: rec.business_domain == "expense"
        ):
            applicability.display_account_prefix = True


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_account_in_analytic_distribution(self):
        self.env.cr.execute(
            SQL(
                r"""
                SELECT id FROM hr_expense
                    WHERE %s && %s
                LIMIT 1
                """,
                [str(account_id) for account_id in self.ids],
                self.env["hr.expense"]._query_analytic_accounts(),
            )
        )
        expense_ids = self.env.cr.fetchall()
        if expense_ids:
            _debug.logic(
                "analytic_unlink_refused", accounts=self, expense=expense_ids[0][0]
            )
            raise UserError(
                _("You cannot delete an analytic account that is used in an expense.")
            )
