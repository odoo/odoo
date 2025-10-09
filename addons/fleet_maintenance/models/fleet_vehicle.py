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
