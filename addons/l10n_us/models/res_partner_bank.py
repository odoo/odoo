# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import models, api, _
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.constrains('clearing_number')
    def _check_clearing_number_us(self):
        for bank in self:
            if self.env.company.country_code == 'US' and bank.clearing_number and not re.match(r'^\d{1,9}$', bank.clearing_number):
                raise ValidationError(_('ABA/Routing should only contains numbers (maximum 9 digits).'))
