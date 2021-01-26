from odoo import models, fields, api

class SalonBookingPayment(models.TransientModel):
    _name = 'salon.booking.payment'
    
    qr_code_booking_payment = fields.Binary(string="QR Code",attachment=True,store=True,help="This field holds the QR Code image used for payment purpose")
    aba_account_name = fields.Char(string="ABA Account Name")
    aba_account_id = fields.Char(string = "ABA Account ID")
    activate_booking_payment = fields.Boolean(string="Activate booking payments")


