# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountPaymentMethod(models.Model):
    _name = "account.payment.method"
    _description = "Payment Methods"
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)  # For internal identification
    payment_type = fields.Selection([('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)
    sequence = fields.Integer(help='Used to order Methods in the form view', default=10)
