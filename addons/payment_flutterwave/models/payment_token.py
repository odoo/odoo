# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import payment


class PaymentToken(payment.PaymentToken):

    flutterwave_customer_email = fields.Char(
        help="The email of the customer at the time the token was created.", readonly=True
    )
