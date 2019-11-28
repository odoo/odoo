# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models,  _
from odoo.exceptions import ValidationError

# TODO: Move Luhn-algorithm to utility class
def validate_luhn(acc_number):
    n = len(acc_number)
    digits = [int(d) for d in re.sub(r'\D', '', acc_number)][-n:]
    even_digitsum = sum(x if x < 5 else x - 9 for x in digits[::2])
    return 0 == sum(digits, even_digitsum) % 10


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def _get_supported_account_types(self):
        rslt = super(ResPartnerBank, self)._get_supported_account_types()
        rslt.append(('plusgiro', _('Plusgiro')))
        rslt.append(('bankgiro', _('Bankgiro')))

        return rslt

    @api.model
    def retrieve_acc_type(self, acc_number):
        if acc_number and re.match('\d{5,7}-\d{1}', acc_number):
            return 'plusgiro'
        elif acc_number and re.match('\d{3,4}-\d{4}', acc_number):
            return 'bankgiro'
        else:
            super(ResPartnerBank, bank).retrieve_acc_type(acc_number)

    @api.constrains('acc_number')
    def acc_number_constrains(self):
        for record in self:
            if record.acc_type == 'plusgiro':
                if not validate_luhn(record.acc_number):
                    raise ValidationError(_('The Plusgiro account is not correct.'))
            elif record.acc_type == 'bankgiro':
                if not validate_luhn(record.acc_number):
                    raise ValidationError(_('The Bankgiro account is not correct.'))
