# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    equipment_ids = fields.One2many('maintenance.equipment', 'vehicle_id')
    equipment_count = fields.Integer('Equipment Count', compute='_compute_equipment_count')

    @api.depends('equipment_ids')
    def _compute_equipment_count(self):
        for employee in self:
            employee.equipment_count = len(employee.equipment_ids)

    def open_assigned_equipment(self):
        self.ensure_one()
        return {
            'name': 'Assigned Equipment',
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.equipment',
            'domain': [('equipment_assign_to', '=', 'vehicle'), ('vehicle_id', '=', self.id)],
            'view_mode': 'list',
            'context': {
                'create': 0,
            }
        }
