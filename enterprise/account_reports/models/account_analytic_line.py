from odoo import api, fields, models
from odoo.tools import Query, SQL


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    analytic_coverage = fields.Float(
        string="Analytic Coverage",
        compute='_compute_analytic_coverage',
    )

    def _field_to_sql(self, alias: str, fname: str, query: (Query | None) = None, flush: bool = True) -> SQL:
        if fname == 'analytic_coverage':
            plan_id = self.env.context.get('selected_analytic_plan')
            if not plan_id:
                return SQL("0.0")

            move_line_alias = query.left_join(
                alias, 'move_line_id',
                'account_move_line', 'id',
                'move_line_id',
            )

            column_name = self.env['account.analytic.plan'].browse(plan_id)._column_name()
            account_alias = query.left_join(
                alias, column_name,
                'account_analytic_account', 'id',
                column_name,
            )

            plan_alias = query.left_join(
                account_alias, 'plan_id',
                'account_analytic_plan', 'id',
                'plan_id',
            )

            amount_sql = SQL(
                "CASE WHEN %s = %s THEN %s ELSE 0 END",
                SQL.identifier(plan_alias, 'id'),
                plan_id,
                SQL.identifier(alias, 'amount'),
            )
            return SQL(
                "COALESCE(-(%(amount)s / NULLIF(%(balance)s, 0)), 0)",
                amount=amount_sql,
                balance=SQL.identifier(move_line_alias, 'balance'),
            )

        return super()._field_to_sql(alias, fname, query, flush)

    @api.depends('amount', 'move_line_id.balance', 'auto_account_id')
    def _compute_analytic_coverage(self):
        plan_id = self.env.context.get('selected_analytic_plan')
        self.analytic_coverage = 0.0
        if plan_id:
            for line in self:
                analytic_account = line.with_context(analytic_plan_id=plan_id).auto_account_id
                if analytic_account and analytic_account.plan_id.id == plan_id:
                    line.analytic_coverage = - line.amount / line.move_line_id.balance if line.move_line_id.balance else 0.0
