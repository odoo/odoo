from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import Query


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    crossovered_budget_line = fields.One2many(
        'crossovered.budget.lines', 'analytic_account_id', 'Budget Lines'
    )


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def _where_calc(self, domain, active_test=True):
        domain = Domain(domain or [])
        if (
            self._active_name
            and active_test
            and self.env.context.get("active_test", True)
            and not any(leaf.field_expr == self._active_name for leaf in domain.iter_conditions())
        ):
            domain &= Domain(self._active_name, "=", True)

        domain = domain.optimize_full(self)
        if domain.is_false():
            return self.browse()._as_query()

        query = Query(self.env, self._table, self._table_sql)
        if not domain.is_true():
            query.add_where(domain._to_sql(self, self._table, query))
        return query
