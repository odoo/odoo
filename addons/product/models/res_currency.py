    # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.constrains('rounding')
    def _check_main_currency_rounding(self):
        decimal_precision = self.env['decimal.precision'].search([('name', 'like', 'Account')], limit=1)
        main_currency = self.env.user.company_id.currency_id
        for currency in self:
            if decimal_precision and currency == main_currency and \
                    float_compare(main_currency.rounding, 10 ** -decimal_precision.digits, precision_digits=6) == -1:
                raise ValidationError(_("Error! You cannot define a rounding factor for the company\'s main currency that is smaller than the decimal precision of \'Account\'."))
