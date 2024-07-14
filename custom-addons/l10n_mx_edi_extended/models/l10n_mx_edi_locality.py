# -*- coding: utf-8 -*-
from odoo import fields, models


class L10nMxEdiResLocality(models.Model):
    _name = 'l10n_mx_edi.res.locality'
    _description = 'Locality'

    name = fields.Char(required=True, translate=True)
    country_id = fields.Many2one(
        'res.country', string='Country', required=True)
    state_id = fields.Many2one(
        'res.country.state', 'State',
        domain="[('country_id', '=', country_id)]", required=True)
    code = fields.Char()
