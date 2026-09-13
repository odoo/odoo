from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = "payment.token"

    adyen_shopper_reference = fields.Char(
        string="Shopper Reference",
        readonly=True,
        help="The unique reference of the partner owning this token",
    )
