# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_co_pos_serial_number = fields.Char(string="POS Serial Number")
