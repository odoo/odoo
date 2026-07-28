# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    aba_routing = fields.Char(string="ABA/Routing", help="American Bankers Association Routing Number")

    @api.constrains('aba_routing')
    def _check_aba_routing(self):
        for bank in self:
            if bank.aba_routing and not re.match(r'^\d{1,9}$', bank.aba_routing):
                raise ValidationError(_('ABA/Routing should only contains numbers (maximum 9 digits).'))
