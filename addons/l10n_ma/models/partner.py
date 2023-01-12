# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Partner(models.Model):
    _inherit= 'res.partner'

    l10n_ma_ice = fields.Char(string="ICE", size=15)
