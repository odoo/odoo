from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = "payment.token"

    flutterwave_customer_email = fields.Char(
        readonly=True,
        help="The email of the customer at the time the token was created.",
    )
