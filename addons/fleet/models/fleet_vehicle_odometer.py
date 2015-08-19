# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from openerp import api, fields, models


class FleetVehicleOdometer(models.Model):

    _name = 'fleet.vehicle.odometer'
    _description = 'Odometer log for a vehicle'
    _order = 'date desc'

    name = fields.Char(compute='_compute_vehicle_log_name', store=True)
    date = fields.Date(default=fields.Date.context_today)
    value = fields.Float('Odometer Value', group_operator="max")
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    unit = fields.Selection(related='vehicle_id.odometer_unit', readonly=True)

    @api.one
    @api.depends('vehicle_id', 'date')
    def _compute_vehicle_log_name(self):
        name = self.vehicle_id and self.vehicle_id.name or ''
        self.name = self.date and name + ' / ' + self.date or name
