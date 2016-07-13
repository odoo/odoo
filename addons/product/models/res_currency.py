# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools, _
from odoo.exceptions import ValidationError


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.constrains('rounding')
    def _check_main_currency_rounding(self):
        account_precision = self.env['decimal.precision'].search([('name', '=', 'Account')])
        if any(currency == self.env.user.company_id.currency_id and
                tools.float_compare(self.env.user.company_id.currency_id.rounding, 10 ** - account_precision.digits, precision_digits=6) == -1
                for currency in self):
            raise ValidationError(_("You cannot define a rounding factor for the company's main currency that is smaller than the decimal precision of 'Account'."))
        return True
