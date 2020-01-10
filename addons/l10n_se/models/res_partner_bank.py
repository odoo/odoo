# -*- coding: utf-8 -*-
import re
import logging
from odoo import api, fields, models,  _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

def validate_luhn(acc_number):
    digits = [int(d) for d in re.sub(r'\D', '', acc_number)]
    even_digitsum = sum(x if x < 5 else x - 9 for x in digits[::2])
    return 0 == sum(digits, even_digitsum) % 10

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def _get_supported_account_types(self):
        rslt = super(ResPartnerBank, self)._get_supported_account_types()
        rslt.append(('plusgiro', _('Plusgiro')))
        rslt.append(('bankgiro', _('Bankgiro')))
        rslt.append(('kontonummer', _('Kontonummer')))

        return rslt

    @api.model
    def _validate_kontonummer(self, acc_number):
        acc = acc_number.split(',')

        if len(acc) != 2:
            raise ValidationError(_('Clearing Number or Account Number is missing.'))
        if not self.bank_id:
            self.bank_id = self.env['res.bank'].get_bank_id_from_clearing(acc[0])
        if self.env['res.bank'].get_bank_id_from_clearing(acc[0]) == self.bank_id.id:
            raise ValidationError(_('Clearing Number is not correct for %s.') % self.bank_id.name)
        if len(re.sub(r'\D', '', acc[1])) != self.bank_id.account_digits:
            raise ValidationError(_('Number of Account Digits for %s is not correct. Number of Account Digits should be %s digits.') % (self.bank_id.name, self.bank_id.account_digits))
        if not validate_luhn(acc[1]):
            raise ValidationError(_('Account Number for %s is not correct.') % self.bank_id.name)

    @api.model
    def retrieve_acc_type(self, acc_number):
        if acc_number and re.fullmatch('\d{5,7}-\d{1}', acc_number):
            return 'plusgiro'
        elif acc_number and re.fullmatch('\d{3,4}-\d{4}', acc_number):
            return 'bankgiro'
        elif acc_number and re.fullmatch('\d{4,4},\d{6,9}-\d{1}', acc_number):
            return 'kontonummer'
        
        return super(ResPartnerBank, self).retrieve_acc_type(acc_number)

    @api.one
    @api.constrains('acc_number')
    def _check_giro(self):
        if (self.acc_type == 'plusgiro' or self.acc_type == 'bankgiro') and not validate_luhn(self.acc_number):
            raise ValidationError(_('The account number for %s is not correct.') % self.acc_type)
        if self.acc_type == 'kontonummer':
            self._validate_kontonummer(self.acc_number)
