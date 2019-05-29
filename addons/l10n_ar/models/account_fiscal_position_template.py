# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountFiscalPositionTemplate(models.Model):

    _inherit = 'account.fiscal.position.template'

    l10n_ar_afip_responsability_type_codes = fields.Char(
        'AFIP Responsability Type Codes',
    )
