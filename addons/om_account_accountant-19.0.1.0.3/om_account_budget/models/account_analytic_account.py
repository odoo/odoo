from odoo import fields, models, api


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    crossovered_budget_line = fields.One2many(
        'crossovered.budget.lines', 'analytic_account_id', 'Budget Lines'
    )


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def _where_calc(self, domain, active_test=True):
        """Computes the WHERE clause needed to implement an OpenERP domain.

        :param list domain: the domain to compute
        :param bool active_test: whether the default filtering of records with
            ``active`` field set to ``False`` should be applied.
        :return: the query expressing the given domain as provided in domain
        :rtype: Query
        """
        # if the object has an active field ('active', 'x_active'), filter out all
        # inactive records unless they were explicitly asked for
        if self._active_name and active_test and self._context.get('active_test', True):
            # the item[0] trick below works for domain items and '&'/'|'/'!'
            # operators too
            if not any(item[0] == self._active_name for item in domain):
                domain = [(self._active_name, '=', 1)] + domain

        if domain:
            return expression.expression(domain, self).query
        else:
            return Query(self.env, self._table, self._table_sql)

