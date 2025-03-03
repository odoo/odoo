from odoo import models, fields

class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Hotel Room'

    name = fields.Char(string='Room Name', required=True)
    room_type = fields.Selection([('single', 'Single'), ('double', 'Double')], string='Room Type')
    rate = fields.Float(string='Rate per Night')
    availability = fields.Boolean(string='Available', default=True)
