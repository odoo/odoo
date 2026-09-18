from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, Query

_debug = DebugLog(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    analytic_coverage = fields.Float(
        compute="_compute_analytic_coverage",
        value_sql="_analytic_coverage_sql",
    )

    @_debug.perf.timed
    def _analytic_coverage_sql(
        self, field: fields.Field, alias: str, query: (Query | None) = None
    ) -> SQL:
        if query is None:
            raise ValueError("analytic_coverage needs a query to hang its joins on")
        plan_id = self.env.context.get("selected_analytic_plan")
        _debug.logic("analytic_coverage_sql_mode", plan=plan_id, constant=not plan_id)
        if not plan_id:
            return SQL("0.0")

        move_line_alias = query.left_join(
            alias,
            "move_line_id",
            "account_move_line",
            "id",
            "move_line_id",
        )

        column_name = self.env["account.analytic.plan"].browse(plan_id)._column_name()
        account_alias = query.left_join(
            alias,
            column_name,
            "account_analytic_account",
            "id",
            column_name,
        )

        plan_alias = query.left_join(
            account_alias,
            "plan_id",
            "account_analytic_plan",
            "id",
            "plan_id",
        )

        amount_sql = SQL(
            "CASE WHEN %s = %s THEN %s ELSE 0 END",
            SQL.identifier(plan_alias, "id"),
            plan_id,
            SQL.identifier(alias, "amount"),
        )
        return SQL(
            "COALESCE(-(%(amount)s / NULLIF(%(balance)s, 0)), 0)",
            amount=amount_sql,
            balance=SQL.identifier(move_line_alias, "balance"),
        )

    @api.depends("amount", "move_line_id.balance", "auto_account_id")
    def _compute_analytic_coverage(self):
        plan_id = self.env.context.get("selected_analytic_plan")
        self.analytic_coverage = 0.0
        if plan_id:
            for line in self:
                analytic_account = line.with_context(
                    analytic_plan_id=plan_id
                ).auto_account_id
                if analytic_account and analytic_account.plan_id.id == plan_id:
                    line.analytic_coverage = (
                        -line.amount / line.move_line_id.balance
                        if line.move_line_id.balance
                        else 0.0
                    )
