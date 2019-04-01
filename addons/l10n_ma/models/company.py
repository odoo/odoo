# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    l10n_ma_ice = fields.Char(string='ICE', size=15, related="partner_id.l10n_ma_ice", readonly=False)
