# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountTaxINherit(models.Model):
    _inherit = 'account.tax'

    is_non_zero_vat = fields.Selection(string="Is Vat (V)", selection=[('is_vat', 'Is Vat (V)'), ('is_non_vat', 'Is Non Vat (E)'), ('is_zero_vat', 'Is Zero Vat (Z)')])
