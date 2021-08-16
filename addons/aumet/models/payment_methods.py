from odoo import models, fields


class PaymentMethod(models.Model):
    _name = 'aumet.payment_method'
    marketplace_payment_method_id = fields.Integer("Payment Method Id")
    name = fields.Char(string="Payment Method")

