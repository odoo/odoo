# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class DecimalPrecision(models.Model):
    _inherit = 'decimal.precision'

    @api.constrains('digits')
    def _check_main_currency_rounding(self):
        decimal_precision = self.search([('name', 'like', 'Account')], limit=1)
        main_currency = self.env.user.company_id.currency_id
        if decimal_precision and self == decimal_precision and \
                float_compare(main_currency.rounding, 10 ** -decimal_precision.digits, precision_digits=6) == -1:
            raise ValidationError(_("Error! You cannot define the decimal precision of \'Account\' as greater than the rounding factor of the company\'s main currency"))
        return True
