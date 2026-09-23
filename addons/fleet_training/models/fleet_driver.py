from odoo import api, fields, models


class FleetDriver(models.Model):
    _name = 'fleet_training.driver'
    _description = 'Fleet Driver'
    _order = 'name'

    name = fields.Char(required=True)
    license_number = fields.Char(string="Driving License No.")
    phone = fields.Char()
    email = fields.Char()
    hire_date = fields.Date()
    active = fields.Boolean(default=True)

    vehicle_ids = fields.One2many('fleet_training.vehicle', 'driver_id', string="Assigned Vehicles")
    vehicle_count = fields.Integer(string="# Vehicles", compute='_compute_vehicle_count')

    @api.depends('vehicle_ids')
    def _compute_vehicle_count(self):
        for driver in self:
            driver.vehicle_count = len(driver.vehicle_ids)
