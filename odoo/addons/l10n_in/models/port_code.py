# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nInPortCode(models.Model):
    """Port code must be mentioned in export and import of goods under GST."""
    _name = 'l10n_in.port.code'
    _description = "Indian port code"
    _rec_name = 'code'

    code = fields.Char(string="Port Code", required=True)
    name = fields.Char(string="Port", required=True)
    state_id = fields.Many2one('res.country.state', string="State")

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The Port Code must be unique!')
    ]
