# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountFiscalPositionTemplate(models.Model):

    _inherit = 'account.fiscal.position.template'

    l10n_ar_afip_code = fields.Char(
        'AFIP Code',
        help='This code will be used on electronic invoice and citi '
        'reports',
    )
