from odoo import models, fields, api

class SalonBookingEmail(models.TransientModel):
    _name = 'salon.booking.email'
    
    booking_email_sender = fields.Char(string="Booking Email Sender")
    booking_email_pass = fields.Char(string="Booking Email Sender Password")
    booking_email_receiver = fields.Char(string="Booking Email Receiver")
    booking_smtp_host = fields.Char(string="SMTP Host",)
    booking_smtp_port = fields.Integer(string="SMTP Port",)



