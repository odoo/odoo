# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging


from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.iap.models import iap
from odoo.addons.iap.models.iap import InsufficientCreditError

_logger = logging.getLogger(__name__)

try:
    import phonenumbers
    _sms_phonenumbers_lib_imported = True

except ImportError:
    _sms_phonenumbers_lib_imported = False
    _logger.info(
        "The `phonenumbers` Python module is not available. "
        "Phone number validation will be skipped. "
        "Try `pip3 install phonenumbers` to install it."
    )

ERROR_CODES = [
    'MISSING_NUMBER',
    'WRONG_NUMBER_FORMAT',
    'INSUFFICIENT_CREDIT'
]


class Sms(models.Model):
    _name = 'sms.sms'
    _description = 'SMS'

    user_id = fields.Many2one('res.users', 'Sent by')
    partner_id = fields.Many2one('res.partner', 'Recipient', required=True)
    number = fields.Char('Number', required=True)

    body = fields.Text(required=True)
    message_id = fields.Many2one('mail.message', string="SMS Message")

    state = fields.Selection([
        ('pending', 'In Queue'),
        ('sent', 'Sent'),
        ('error', 'Error'),
        ('canceled', 'Canceled')
    ], 'SMS Status', readonly=True, copy=False, default='pending', required=True)
    error_code = fields.Selection([(err_code, err_code) for err_code in ERROR_CODES], string="Error", default='')

    @api.multi
    def send_sms(self):
        for sms in self:
            if not sms.number:
                sms.state = 'error'
                sms.error_code = 'MISSING_NUMBER'
            elif not self._check_number_format(sms.partner_id, sms.number):
                sms.state = 'error'
                sms.error_code = 'WRONG_NUMBER_FORMAT'
            else:
                try:
                    number = self._sms_sanitization(sms.partner_id, sms.number)
                    self.env['sms.api']._send_sms([number], sms.body)
                    sms.state = 'sent'
                except InsufficientCreditError as e:
                    sms.state = 'error'
                    sms.error_code = 'INSUFFICIENT_CREDIT'

    @api.multi
    def cancel_sms(self):
        self.write({'state': 'canceled', 'error_code': False})

    def _phone_get_country(self, partner):
        if 'country_id' in partner:
            return partner.country_id
        return self.env.user.company_id.country_id

    def _check_number_format(self, partner, number):
        if number and _sms_phonenumbers_lib_imported:
            country = self._phone_get_country(partner)
            country_code = country.code if country else None
            try:
                phone_nbr = phonenumbers.parse(number, region=country_code, keep_raw_input=True)
            except phonenumbers.phonenumberutil.NumberParseException:
                return False
            if not phonenumbers.is_possible_number(phone_nbr) or not phonenumbers.is_valid_number(phone_nbr):
                return False
        return True

    def _sms_sanitization(self, partner, number):
        if number and _sms_phonenumbers_lib_imported:
            country = self._phone_get_country(partner)
            country_code = country.code if country else None
            # we know that it won't throw exception
            phone_nbr = phonenumbers.parse(number, region=country_code, keep_raw_input=True)
            if not phonenumbers.is_possible_number(phone_nbr) or not phonenumbers.is_valid_number(phone_nbr):
                return number
            phone_fmt = phonenumbers.PhoneNumberFormat.INTERNATIONAL
            return phonenumbers.format_number(phone_nbr, phone_fmt).replace(' ', '')
        else:
            return number
