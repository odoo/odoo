# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    mercado_pago_customer_id = fields.Char(
        help="Mercado Pago's id of the customer at the time the token was created.", readonly=True
    )
