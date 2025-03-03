from odoo import models, fields, api

class HotelBooking(models.Model):
    _name = 'hotel.booking'
    _description = 'Hotel Booking'

    room_id = fields.Many2one('hotel.room', string='Room')
    guest_id = fields.Many2one('hotel.guest', string='Guest')
    check_in = fields.Datetime(string='Check In')
    check_out = fields.Datetime(string='Check Out')
    total_amount = fields.Float(compute='_compute_total', string='Total Amount')

    @api.depends('room_id', 'check_in', 'check_out')
    def _compute_total(self):
        # Compute total based on room rate and stay duration
        pass
