from odoo import models, fields

class HotelGuest(models.Model):
    _name = 'hotel.guest'
    _description = 'Hotel Guest'

    name = fields.Char(string='Guest Name', required=True)
    contact = fields.Char(string='Contact Information')
