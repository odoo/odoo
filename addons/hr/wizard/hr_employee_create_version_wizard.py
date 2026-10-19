from odoo import models, fields


class HrEmployeeCreateVersionWizard(models.TransientModel):
    _name = 'hr.employee.create.version.wizard'
    _description = 'Create New Employee Version Wizard'

    date_version = fields.Date(string='Start Date', required=True)
    employee_count = fields.Integer(compute='_compute_employee_count', readonly=True)

    def _compute_employee_count(self):
        for wizard in self:
            wizard.employee_count = len(self.env.context.get('active_ids', []))

    def action_create_versions(self):
        self.ensure_one()

        employees = self.env['hr.employee'].browse(
            self.env.context.get('active_ids', []),
        )

        for employee in employees:
            employee.create_version({
                'date_version': self.date_version,
            })

        return {'type': 'ir.actions.act_window_close'}
