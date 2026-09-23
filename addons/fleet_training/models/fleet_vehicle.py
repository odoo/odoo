from odoo import fields, models


class FleetVehicle(models.Model):
    _name = 'fleet_training.vehicle'
    _description = 'Fleet Vehicle'
    _order = 'name'

    name = fields.Char(required=True, help="Internal fleet reference, e.g. 'Fleet-001'.")
    license_plate = fields.Char()
    vin_sn = fields.Char(string="Chassis Number")
    color = fields.Char()
    model_year = fields.Integer(string="Model Year")
    seats = fields.Integer(default=5)
    acquisition_date = fields.Date()
    active = fields.Boolean(default=True)
    notes = fields.Text()

    driver_id = fields.Many2one('fleet_training.driver', string="Assigned Driver")
    category_id = fields.Many2one('fleet_training.category', string="Category")
    tag_ids = fields.Many2many('fleet_training.tag', string="Tags")
