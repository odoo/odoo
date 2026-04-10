# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = "payment.token"

    paypal_customer_id = fields.Char(string="Paypal Vault Customer ID")
