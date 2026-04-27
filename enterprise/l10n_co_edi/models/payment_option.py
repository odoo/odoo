# coding: utf-8
from odoo import fields, models


class PaymentOptions(models.Model):
    _name = 'l10n_co_edi.payment.option'
    _description = 'Colombian Payment Options'

    code = fields.Char(string="Code")
    name = fields.Char(string="Payment Option")
