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
        if version_to_split.date_version == self.effective_date:
            raise UserError(_('A version already exists on that effective date'))
        new_version = version_to_split.copy()
        new_version.date_version = self.effective_date
        new_version.employee_id = version_to_split.employee_id
        new_version.employee_id.version_id = new_version
        # print(new_version, new_version.date_version, new_version.employee_id)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Employees',
            'path': 'employee',
            'res_model': 'hr.employee',
            'res_id': new_version.employee_id.id,
            'view_mode': 'form',
            'context': {
                'version_id': new_version.id,
            }
        }
        return {'type': 'ir.actions.client', 'tag': 'reload', 'context': {'version_id': new_version.id}}
