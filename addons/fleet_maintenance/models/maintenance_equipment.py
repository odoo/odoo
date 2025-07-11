# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    equipment_assign_to = fields.Selection(selection_add=[('vehicle', 'Vehicle'), ('other', 'Other')], default='vehicle')
    # check ondelete on above
    vehicle_id = fields.Many2one('fleet.vehicle', compute='_compute_vehicle_id',
        store=True, readonly=False, string="Vehicle", tracking=True)

    @api.depends('equipment_assign_to', 'vehicle_id')
    def _compute_owner(self):
        super()._compute_owner()
        for equipment in self:
            if equipment.equipment_assign_to == 'vehicle':
                equipment.owner_user_id = equipment.vehicle_id.manager_id if equipment.vehicle_id.manager_id else self.env.user.id
            elif equipment.equipment_assign_to == 'other':
                equipment.owner_user_id = self.env.user.id

    @api.depends('equipment_assign_to')
    def _compute_vehicle_id(self):
        for equipment in self:
            if equipment.equipment_assign_to == 'vehicle':
                equipment.vehicle_id = equipment.vehicle_id
                if 'employee_id' in equipment._fields:
                    equipment.employee_id = False
                if 'department_id' in equipment._fields:
                    equipment.department_id = False
            else:
                equipment.vehicle_id = equipment.vehicle_id
