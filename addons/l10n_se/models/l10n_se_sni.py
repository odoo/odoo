# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class L10nSeSni(models.Model):
    """SNI 2025 industry classification codes (Svensk Näringsgrensindelning).

    Flat list of 5-digit class-level codes as published by SCB.
    """

    _name = 'l10n_se.sni'
    _description = 'SNI 2025 Industry Classification'
    _rec_name = 'code'
    _rec_names_search = ['code', 'name']
    _order = 'code'

    _unique_code = models.Constraint('unique(code)', 'SNI code must be unique.')
    _code_format = models.Constraint("CHECK (code ~ '^[0-9]{5}$')", 'SNI code must be exactly 5 digits.')

    code = fields.Char(required=True, index=True, size=5)
    name = fields.Char(required=True, translate=True)

    @api.depends('code', 'name')
    def _compute_display_name(self):
        """Display name as SCB writes it: 01.110 Name."""
        for rec in self:
            rec.display_name = f'{rec.code[:2]}.{rec.code[2:]} {rec.name}' if rec.code else rec.name
