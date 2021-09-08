from odoo import models, fields


class PaymentMethod(models.Model):
    _name = 'aumet.payment_method'
    _description = 'Aumet Payment Method'

    marketplace_payment_method_id = fields.Integer("Payment Method Id")
    name = fields.Char(string="Payment Method")

    _sql_constraints = [
        ('marketplace_payment_method_id_uniq', 'unique(marketplace_payment_method_id)', "Payment method already exist"),
    ]
