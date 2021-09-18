# -*- coding: utf-8 -*-
from odoo import models, fields


class PaymentMethod(models.Model):
    _name = 'aumet.payment.method'
    _description = 'Aumet Payment Method'

    name = fields.Char(string='Name', required=True, readonly=True)
    payment_method_id = fields.Integer(string='Aumet ID', required=True, readonly=True)
    discount = fields.Float(string='Discount', readonly=True)
    unit_price = fields.Float(string='Unit Price', readonly=True)
    discount_expire_date = fields.Date(string='Discount Expire Date', readonly=True)
