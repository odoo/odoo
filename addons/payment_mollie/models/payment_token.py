# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    mollie_customer_id = fields.Char(string="Mollie Customer ID", readonly=True)
