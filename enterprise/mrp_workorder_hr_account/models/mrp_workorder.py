from odoo import _, models, fields


class MrpWorkcenterProductivity(models.Model):
    _inherit = "mrp.workcenter.productivity"

    def _prepare_analytic_line_values(self, account, amount, unit_amount):
        self.ensure_one()
        res = self.workorder_id._prepare_analytic_line_values(account, amount, unit_amount)
        res['name'] = _("[EMPL] %(work_order)s - %(employee)s", work_order=self.workorder_id.display_name, employee=self.employee_id.name)
        res['employee_id'] = self.employee_id.id
        return res


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    employee_analytic_account_line_ids = fields.Many2many('account.analytic.line', copy=False)

    def _compute_duration(self):
        super()._compute_duration()
        self._create_or_update_analytic_entry()

    def action_cancel(self):
        self.employee_analytic_account_line_ids.unlink()
        return super().action_cancel()
