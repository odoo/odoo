from odoo import models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    # ----------------------------
    #  Actions
    # ----------------------------

    def _get_expense_action(self, domain=None, expense_ids=None):
        if not domain and not expense_ids:
            return {}
        action = self.env["ir.actions.actions"]._for_xml_id("hr_expense.hr_expense_actions_all")
        action.update({
            'display_name': self.env._('Expenses'),
            'views': [[False, 'list'], [False, 'form'], [False, 'kanban'], [False, 'graph'], [False, 'pivot']],
            'context': {'project_id': self.id},
            'domain': domain or [('id', 'in', expense_ids)],
        })
        if not self.env.context.get('from_embedded_action') and len(expense_ids) == 1:
            action["views"] = [[False, 'form']]
            action["res_id"] = expense_ids[0]
        return action

    def action_open_project_expenses(self):
        self.ensure_one()
        return self._get_expense_action(domain=[('analytic_distribution', 'in', self.account_id.ids)])
