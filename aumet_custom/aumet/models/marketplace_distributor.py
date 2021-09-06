from odoo import models, fields


class PaymentMethod(models.Model):
    _name = 'aumet.marketplace_distributor'
    marketplace_id = fields.Integer("Payment Method Id")
    name = fields.Char(string="Distributor ")
    country_id = fields.Integer("Country ID")

    _sql_constraints = [
        ('marketplace_payment_method_id_uniq', 'unique(marketplace_payment_method_id)', "Payment method already exist"),
    ]
