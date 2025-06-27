from odoo import api, models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    equipment_ids = fields.One2many('maintenance.equipment', 'employee_id', groups="hr.group_hr_user")
    equipment_count = fields.Integer('Equipment Count', compute='_compute_equipment_count')
    departure_do_unassign_equipment = fields.Boolean(related='version_id.departure_do_unassign_equipment',
        inherited=True, readonly=False, groups="hr.group_hr_user")

    @api.depends('equipment_ids')
    def _compute_equipment_count(self):
        for employee in self:
            employee.equipment_count = len(employee.equipment_ids)
