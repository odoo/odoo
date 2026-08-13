# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Expense(models.Model):
    _inherit = "hr.expense"

    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        if not self.env.context.get('project_id'):
            expenses_to_recompute = self.env['hr.expense']
            prefetch_ids = set()
            for expense in self.filtered('sale_order_id'):
                expenses_to_recompute += expense
                prefetch_ids.update(self.env['analytic.mixin']._get_analytic_account_ids_from_distributions(expense.analytic_distribution))
                prefetch_ids.update(self.env['analytic.mixin']._get_analytic_account_ids_from_distributions(expense.sale_order_id.project_id._get_analytic_distribution()))

            if expenses_to_recompute:
                analytic_account_model = self.env['account.analytic.account'].with_prefetch(prefetch_ids)
                for expense in expenses_to_recompute:
                    expense_account_ids = self.env['analytic.mixin']._get_analytic_account_ids_from_distributions(expense.analytic_distribution)
                    project_analytic_distribution = expense.sale_order_id.project_id._get_analytic_distribution()
                    project_account_ids = self.env['analytic.mixin']._get_analytic_account_ids_from_distributions(project_analytic_distribution)

                    project_analytic_distribution_accounts = self.env['account.analytic.account'].browse(project_account_ids)
                    expense_analytic_accounts = analytic_account_model.browse(expense_account_ids)

                    if not any(project_account.root_plan_id in expense_analytic_accounts.root_plan_id for project_account in project_analytic_distribution_accounts):
                        # If it is possible we keep both analytic distributions
                        expense.analytic_distribution = {
                            **(expense.analytic_distribution or {}),
                            **(project_analytic_distribution or {})
                        }
                    else:
                        # If not we keep the most prioritized one -> project
                        expense.analytic_distribution = expense.sale_order_id.project_id._get_analytic_distribution() or expense.analytic_distribution or {}
