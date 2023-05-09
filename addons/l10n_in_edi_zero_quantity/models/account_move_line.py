# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    l10n_in_edi_is_zero_quantity = fields.Boolean(string="Zero Quantity")
