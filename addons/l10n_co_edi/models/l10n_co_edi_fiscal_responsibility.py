# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nCoEdiFiscalResponsibility(models.Model):
    _name = 'l10n_co_edi.fiscal.responsibility'
    _description = 'DIAN Fiscal Responsibility Code'
    _order = 'code'

    code = fields.Char(
        string='Code', required=True,
        help='DIAN fiscal responsibility code (e.g., O-13, O-15, R-99-PN).',
    )
    name = fields.Char(
        string='Description', required=True, translate=True,
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Fiscal responsibility code must be unique.'),
    ]

    def name_get(self):
        return [(rec.id, f"{rec.code} - {rec.name}") for rec in self]
