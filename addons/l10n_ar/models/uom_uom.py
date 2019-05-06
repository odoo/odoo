# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class Uom(models.Model):

    _inherit = 'uom.uom'

    l10n_ar_afip_code = fields.Char(
        'AFIP Code',
        help='This code will be used on electronic invoice and citi '
        'reports',
    )
