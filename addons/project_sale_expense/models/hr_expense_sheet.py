# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def _do_create_moves(self):
        """ When creating the move of the expense, if the AA is given in the project of the SO, we take it as reference in the distribution.
            Otherwise, we create a AA for the project of the SO and set the distribution to it.
        """
        for expense in self.expense_line_ids:
            project = expense.sale_order_id.project_id
            if not project or expense.analytic_distribution:
                continue
            if not project.account_id:
                project._create_analytic_account()
            expense.analytic_distribution = project._get_analytic_distribution()
        return super()._do_create_moves()
