from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventTicket(models.Model):
    _inherit = 'event.event.ticket'

    tickets_per_registration = fields.Integer(string="Tickets Per Registration", copy=False, default=0)
