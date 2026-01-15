# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    # Mercado Pago's id of the customer at the time the token was created."
    mercado_pago_customer_id = fields.Char(readonly=True)
