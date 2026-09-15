from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _compute_analytic_distribution(self):
        project_id = self.env.context.get("project_id")
        if not project_id:
            _debug.logic(
                "expense_distribution_delegated",
                reason="no_project_in_context",
                expenses=self,
            )
            super()._compute_analytic_distribution()
        else:
            analytic_distribution = (
                self.env["project.project"]
                .browse(project_id)
                ._get_analytic_distribution()
            )
            for expense in self:
                _debug.logic(
                    "expense_distribution_from_project",
                    expense=expense,
                    project_id=project_id,
                    kept_own=bool(expense.analytic_distribution),
                )
                expense.analytic_distribution = (
                    expense.analytic_distribution or analytic_distribution
                )

    @api.model_create_multi
    def create(self, vals_list):
        project_id = self.env.context.get("project_id")
        if project_id:
            analytic_distribution = (
                self.env["project.project"]
                .browse(project_id)
                ._get_analytic_distribution()
            )
            _debug.pipeline(
                "expense_create_project_distribution",
                project_id=project_id,
                expenses=len(vals_list),
                has_distribution=bool(analytic_distribution),
            )
            if analytic_distribution:
                for vals in vals_list:
                    vals["analytic_distribution"] = vals.get(
                        "analytic_distribution", analytic_distribution
                    )
        return super().create(vals_list)
