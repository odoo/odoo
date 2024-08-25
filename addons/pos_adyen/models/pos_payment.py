from odoo import models, fields

class PosPayment(models.Model):
    _inherit = 'pos.payment'

    adyen_last_secret_key = fields.Char(string="Adyen last secret key", help="""
        When a request for payment is sent to the Adyen server,
        we create this secret key; when the response comes back on the webhook,
        we check it's authenticity by comparing the secret key in the response with this one.
        """, copy=False)
