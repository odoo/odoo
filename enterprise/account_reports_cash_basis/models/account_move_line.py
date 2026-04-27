# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.tools import SQL


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = "account.move.line"

    def _where_calc(self, domain, active_test=True):
        """ In case of cash basis for reports, we need to shadow the table account_move_line to get amounts
        based on cash.
        We also need to get the analytic amounts in the table if we have the analytic grouping on reports.
        """
        query = super()._where_calc(domain, active_test)
        if self.env.context.get('account_report_cash_basis'):
            self.env['account.report']._prepare_lines_for_cash_basis()
            if self.env.context.get('account_report_analytic_groupby'):
                self.env['account.report']._prepare_lines_for_analytic_groupby_with_cash_basis()
                query._tables['account_move_line'] = SQL.identifier('analytic_cash_basis_temp_account_move_line')
            else:
                query._tables['account_move_line'] = SQL.identifier('cash_basis_temp_account_move_line')
        return query
