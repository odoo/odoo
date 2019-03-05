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

except ImportError:
    phonenumbers = False
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
    partner_id = fields.Many2one('res.partner', string='Recipient')
    number = fields.Char()
    body = fields.Text(string='Sms Message', required=True)
    message_id = fields.Many2one('mail.message', string="Thread Message")

    state = fields.Selection([
        ('pending', 'In Queue'),
        ('sent', 'Sent'),
        ('error', 'Error'),
        ('canceled', 'Canceled')
    ], 'SMS Status', readonly=True, copy=False, default='pending')
    error_code = fields.Selection([(err_code, err_code) for err_code in ERROR_CODES], string="Error", default='')

    @api.multi
    def send_sms(self):
        for sms in self:
            sanitized_number = self._sms_sanitization(sms.partner_id, sms.number)
            if not sms.number:
                sms.write({'state': 'error', 'error_code': 'MISSING_NUMBER'})
            elif not sanitized_number:
                sms.write({'state': 'error', 'error_code': 'WRONG_NUMBER_FORMAT'})
            else:
                try:
                    self.env['sms.api']._send_sms([sanitized_number], sms.body)
                    sms.state = 'sent'
                except InsufficientCreditError as e:
                    sms.write({'state': 'error', 'error_code': 'INSUFFICIENT_CREDIT'})

    @api.multi
    def cancel_sms(self):
        self.write({'state': 'canceled', 'error_code': False})

    def _phone_get_country(self, partner):
        if 'country_id' in partner:
            return partner.country_id
        return self.env.user.company_id.country_id

    def _sms_sanitization(self, partner, number):
        if number and phonenumbers:
            country = self._phone_get_country(partner)
            country_code = country.code if country else None
            try:
                phone_nbr = phonenumbers.parse(number, region=country_code, keep_raw_input=True)
            except phonenumbers.phonenumberutil.NumberParseException:
                return False
            if not phonenumbers.is_possible_number(phone_nbr) or not phonenumbers.is_valid_number(phone_nbr):
                return False
            phone_fmt = phonenumbers.PhoneNumberFormat.INTERNATIONAL
            return phonenumbers.format_number(phone_nbr, phone_fmt).replace(' ', '')
        else:
            return number
