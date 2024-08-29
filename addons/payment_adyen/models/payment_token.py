# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import payment

from odoo import _, fields, models


class PaymentToken(models.Model, payment.PaymentToken):

    adyen_shopper_reference = fields.Char(
        string="Shopper Reference", help="The unique reference of the partner owning this token",
        readonly=True)
