from odoo import models, fields


class PaymentTerms(models.Model):
    _name = "payment_terms"
    _description = "Description of the Payment terms model"

    name = fields.Char()
    due_payment_date = fields.Char()
    method = fields.Char()
    amount_calculation = fields.Char()
