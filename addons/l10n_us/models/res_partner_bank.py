# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    show_aba_routing = fields.Boolean(compute="_compute_show_aba_routing")
    l10n_us_bank_account_type = fields.Selection(
        selection=[
            ('checking', 'Checking'),
            ('savings', 'Savings'),
        ],
        string='Bank Account Type',
        default='checking',
        required=True
    )

    @api.depends('country_code', 'acc_type')
    def _compute_show_aba_routing(self):
        for bank in self:
            if bank.country_code == 'US' and bank.acc_type != 'iban':
                bank.show_aba_routing = True
            else:
                bank.show_aba_routing = False

    @api.constrains('clearing_number')
    def _check_clearing_number_us(self):
        for bank in self:
            if bank.country_code == 'US' and bank.clearing_number and not re.match(r'^\d{1,9}$', bank.clearing_number):
                raise ValidationError(_('ABA/Routing should only contain numbers (maximum 9 digits).'))
