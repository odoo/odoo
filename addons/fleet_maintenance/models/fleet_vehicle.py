# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    equipment_ids = fields.One2many('maintenance.equipment', 'vehicle_id')
    equipment_count = fields.Integer(string='Equipment Count', compute='_compute_equipment_count')

    @api.depends('equipment_ids')
    def _compute_equipment_count(self):
        equipment_count_by_vehicle = dict(self.env['maintenance.equipment']._read_group(
            domain=[('vehicle_id', 'in', self.ids)],
            groupby=['vehicle_id'],
            aggregates=['__count'],
        ))
        for vehicle in self:
            vehicle.equipment_count = equipment_count_by_vehicle.get(vehicle, 0)
