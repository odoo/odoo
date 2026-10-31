from odoo import fields, models


class FleetVehicleCategory(models.Model):
    _name = 'fleet_training.category'
    _description = 'Fleet Vehicle Category'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class FleetVehicleTag(models.Model):
    _name = 'fleet_training.tag'
    _description = 'Fleet Vehicle Tag'
    _order = 'name'

    name = fields.Char(required=True)
    color = fields.Integer(string="Color Index")
