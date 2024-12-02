from odoo import models, fields


class PaymentMethod(models.Model):
    _inherit = "payment.method"

    description = fields.Text(string="Description")
    integration_id = fields.Integer(string="Integration ID")
