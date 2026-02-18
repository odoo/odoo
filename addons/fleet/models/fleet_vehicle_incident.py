from odoo import api, fields, models
from odoo.tools import format_datetime


class FleetVehicleIncident(models.Model):
    _name = 'fleet.vehicle.incident'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fleet Incident'

    name = fields.Char(compute='_compute_incident_name', readonly=False, store=True)
    date = fields.Datetime(default=fields.Datetime.now, tracking=True)
    incident_type_id = fields.Many2one('fleet.incident.type',
        default=lambda self: self.env.ref('fleet.fleet_incident_type_accident', raise_if_not_found=False),
        tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True, tracking=True)
    driver_id = fields.Many2one('res.partner', 'Driver', compute='_compute_driver_id', readonly=False,
        tracking=True, store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    is_third_party_involved = fields.Boolean('Third Party Involved?', tracking=True)
    location = fields.Text(tracking=True)
    description = fields.Text(tracking=True)
    state = fields.Selection([
        ('reported', 'Reported'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('cancel', 'Cancelled'),
    ], tracking=True, default='reported')
    tp_driver_name = fields.Char("Driver's Name", tracking=True)
    tp_driver_licence_number = fields.Char("Driver's Licence number", tracking=True)
    tp_driver_email = fields.Char("Driver's Email", tracking=True)
    tp_driver_phone = fields.Char("Driver's Phone Number", tracking=True)
    tp_driver_registration_number = fields.Char("Driver's Registration Number", tracking=True)
    tp_vehicle_registration_number = fields.Char("Vehicle's Registration Number", tracking=True)
    tp_vehicle_damage = fields.Text("Vehicle's Damage", tracking=True)

    @api.depends('vehicle_id', 'date')
    def _compute_incident_name(self):
        for incident in self:
            name = incident.vehicle_id.name
            if not name:
                if incident.date:
                    name = format_datetime(incident.env, incident.date)
            elif incident.date:
                name += ' / ' + format_datetime(incident.env, incident.date)
            incident.name = name

    @api.depends('vehicle_id')
    def _compute_driver_id(self):
        for incident in self:
            incident.driver_id = incident.vehicle_id.driver_id
