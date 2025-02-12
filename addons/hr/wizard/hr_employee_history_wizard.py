# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError


class HrEmployeeVersionWizard(models.TransientModel):
    _name = 'hr.employee.version.wizard'
    _description = 'Employee Version wizard'

    def _get_default_employee_id(self):
        active_id = self.env.context.get('active_id', False)
        if active_id:
            return self.env['hr.employee'].search([('id', '=', active_id)])
        return self.env['hr.employee']

    employee_id = fields.Many2one('hr.employee', default=_get_default_employee_id, readonly=True)
    effective_date = fields.Date(required=True, default=lambda self: fields.Date.today())

    def action_create_new_version(self):
        version_to_split = self.employee_id._get_version(self.effective_date)
        if version_to_split.date_from == self.effective_date:
            raise UserError(_('A version already exists on that effective date'))
        new_version = version_to_split.copy()
        new_version.date_from = self.effective_date
        version_to_split.date_to = self.effective_date - timedelta(days=1)
        self.employee_id.version_ids |= new_version
        self.employee_id.selected_version_id = new_version

        return {'type': 'ir.actions.client', 'tag': 'reload'}
