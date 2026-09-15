from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        if not self.env.context.get("project_id"):
            expenses_to_recompute = self.env["hr.expense"]
            prefetch_ids = set()
            for expense in self.filtered("sale_order_id"):
                expenses_to_recompute += expense
                prefetch_ids.update(
                    self.env[
                        "mixin.analytic"
                    ]._get_analytic_account_ids_from_distributions(
                        expense.analytic_distribution
                    )
                )
                prefetch_ids.update(
                    self.env[
                        "mixin.analytic"
                    ]._get_analytic_account_ids_from_distributions(
                        expense.sale_order_id.project_id._get_analytic_distribution()
                    )
                )

            _debug.pipeline(
                "expense_so_distribution_candidates",
                expenses=self,
                with_sale_order=expenses_to_recompute,
                prefetched_accounts=len(prefetch_ids),
            )
            if expenses_to_recompute:
                analytic_account_model = self.env[
                    "account.analytic.account"
                ].with_prefetch(prefetch_ids)
                for expense in expenses_to_recompute:
                    expense_account_ids = self.env[
                        "mixin.analytic"
                    ]._get_analytic_account_ids_from_distributions(
                        expense.analytic_distribution
                    )
                    project_analytic_distribution = (
                        expense.sale_order_id.project_id._get_analytic_distribution()
                    )
                    project_account_ids = self.env[
                        "mixin.analytic"
                    ]._get_analytic_account_ids_from_distributions(
                        project_analytic_distribution
                    )

                    project_analytic_distribution_accounts = self.env[
                        "account.analytic.account"
                    ].browse(project_account_ids)
                    expense_analytic_accounts = analytic_account_model.browse(
                        expense_account_ids
                    )

                    if not any(
                        project_account.root_plan_id
                        in expense_analytic_accounts.root_plan_id
                        for project_account in project_analytic_distribution_accounts
                    ):
                        _debug.logic(
                            "expense_distribution_merged",
                            reason="no_shared_root_plan",
                            expense=expense,
                            project=expense.sale_order_id.project_id,
                            expense_accounts=expense_analytic_accounts,
                            project_accounts=project_analytic_distribution_accounts,
                        )
                        expense.analytic_distribution = {
                            **(expense.analytic_distribution or {}),
                            **(project_analytic_distribution or {}),
                        }
                    else:
                        _debug.logic(
                            "expense_distribution_replaced",
                            reason="shared_root_plan",
                            expense=expense,
                            project=expense.sale_order_id.project_id,
                            expense_accounts=expense_analytic_accounts,
                            project_accounts=project_analytic_distribution_accounts,
                        )
                        expense.analytic_distribution = (
                            expense.sale_order_id.project_id._get_analytic_distribution()
                            or expense.analytic_distribution
                            or {}
                        )

    def action_post(self):
        for expense in self:
            project = expense.sale_order_id.project_id
            if not project or expense.analytic_distribution:
                _debug.logic(
                    "expense_post_distribution_kept",
                    reason="no_project" if not project else "already_distributed",
                    expense=expense,
                    project=project,
                )
                continue
            if not project.account_id:
                _debug.lifecycle(
                    "project_analytic_account_created",
                    trigger="expense_posted",
                    expense=expense,
                    project=project,
                )
                project._create_analytic_account()
            expense.analytic_distribution = project._get_analytic_distribution()
        return super().action_post()
