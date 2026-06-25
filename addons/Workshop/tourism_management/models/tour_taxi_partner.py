from odoo import models, fields


class TourTaxiPartner(models.Model):
    _name = "tour.taxi.partner"
    _description = "Tour Taxi Partner"

    name = fields.Char(required=True)
    contact_person = fields.Char()
    phone = fields.Char()
    email = fields.Char()
    commission_rate = fields.Float(string="Commission Rate (%)")
    active = fields.Boolean(default=True)
    assignment_ids = fields.One2many("tour.transport.assignment", "taxi_partner_id", string="Transport Assignments")
