# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_account_valuation_correction = fields.Boolean(string="Is valuation correction move", default=False)
