# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class L10nCLCounty(models.Model):
    _name = 'l10n_cl.county'
    _description = 'Chilean Counties'

    name = fields.Char("name")
    type = fields.Selection(
        [('view', 'View'), ('normal', 'Normal')], 'Type', default='normal')
    city = fields.Char('City')
    country_id = fields.Many2one('res.country', string="Country")
