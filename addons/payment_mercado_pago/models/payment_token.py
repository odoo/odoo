# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    mercado_pago_customer_id = fields.Char(
        string="Customer ID", help="The unique reference of the customer owning this token",
        readonly=True)
