# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nCoEdiTaxType(models.Model):
    _name = 'l10n_co_edi.tax.type'
    _description = 'DIAN Tax Type Code'
    _order = 'code'

    code = fields.Char(
        string='Code',
        required=True,
        help='DIAN tax type code used in UBL XML.',
    )
    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
    )
    description = fields.Char(
        string='Description',
        translate=True,
    )
    retention = fields.Boolean(
        string='Is Retention',
        default=False,
        help='Whether this tax type represents a withholding/retention.',
    )

    _unique_code = models.Constraint(
        'UNIQUE(code)',
        'Tax type code must be unique.',
    )
