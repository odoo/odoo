# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError


class HrEmployeeHistoryWizard(models.TransientModel):
    _name = 'hr.employee.history.wizard'
    _description = 'Employee History wizard'

    def _get_default_employee_id(self):
        active_id = self.env.context.get('active_id', False)
        if active_id:
            return self.env['hr.employee'].search([('history_ids.id', '=', active_id)])
        return self.env['hr.employee']

    employee_id = fields.Many2one('hr.employee', default=_get_default_employee_id, readonly=True)
    effective_date = fields.Date(required=True, default=lambda self: fields.Date.today())

    def action_create_new_version(self):
        history_to_split = self.employee_id._get_history(self.effective_date)
        if history_to_split.date_from == self.effective_date:
            raise UserError(_('A version already exists on that effective date'))
        new_history = history_to_split.copy()
        new_history.date_from = self.effective_date
        history_to_split.date_to = self.effective_date - timedelta(days=1)
        self.employee_id.history_ids |= new_history
        self.employee_id.selected_history_id = new_history

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.history',
            'res_id': new_history.id,
            'views': [[False, "form"]],
        }
