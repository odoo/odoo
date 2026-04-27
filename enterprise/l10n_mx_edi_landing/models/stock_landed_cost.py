# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.l10n_mx_edi_extended.models.account_move import CUSTOM_NUMBERS_PATTERN


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    l10n_mx_edi_customs_number = fields.Char(
        help='Optional field for entering the customs information in the case '
        'of first-hand sales of imported goods or in the case of foreign trade'
        ' operations with goods or services.\n'
        'The format must be:\n'
        ' - 2 digits of the year of validation followed by two spaces.\n'
        ' - 2 digits of customs clearance followed by two spaces.\n'
        ' - 4 digits of the serial number followed by two spaces.\n'
        ' - 1 digit corresponding to the last digit of the current year, '
        'except in case of a consolidated customs initiated in the previous '
        'year of the original request for a rectification.\n'
        ' - 6 digits of the progressive numbering of the custom.',
        string='Customs number', size=21, copy=False)

    _sql_constraints = [
        (
            'l10n_mx_edi_customs_number',
            'UNIQUE (l10n_mx_edi_customs_number)',
            'The custom number must be unique!',
        )
    ]

    fiscal_country_codes = fields.Char(related="company_id.country_code")

    @api.constrains('l10n_mx_edi_customs_number')
    def _check_l10n_mx_edi_customs_number(self):
        help_message = self._fields['l10n_mx_edi_customs_number'].help.split('\n', 1)[1]
        for landed_cost in self:
            if not landed_cost.l10n_mx_edi_customs_number:
                continue
            custom_number = landed_cost.l10n_mx_edi_customs_number.strip()
            if not CUSTOM_NUMBERS_PATTERN.match(custom_number):
                raise ValidationError(self.env._(
                    "Error!, The format of the customs number is incorrect. \n%s\n"
                    "For example: 15  48  3009  0001234", help_message))
