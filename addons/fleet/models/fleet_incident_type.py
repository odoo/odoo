from odoo import fields, models


class FleetIncidentType(models.Model):
    _name = 'fleet.incident.type'
    _description = 'Fleet Incident Type'

    name = fields.Char(required=True)
