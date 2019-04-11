# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.addons.iap.models import iap

DEFAULT_ENDPOINT = 'https://iap-sms.odoo.com'


class SmsApi(models.AbstractModel):
    _name = 'sms.api'
    _description = 'SMS API'

    @api.model
    def _send_multi_sms(self, messages):
        """ Send SMS using IAP in batch mode
            :param messages: List of sms to send, with the following form:
                {
                    res_id: ID of sms.sms
                    number: Recipient of the SMS
                    content: Content of the SMS
                }
            
            :return: List of result, with the following form:
                {
                    res_id: ID of sms.sms
                    error: 'insufficient_credit' or 'wrong_format_number' or False
                    credit: Number of credits spent to send this SMS
                }
        """
        account = self.env['iap.account'].sudo().get('sms')
        params = {
            'account_token': account.account_token,
            'messages': messages
        }
        endpoint = self.env['ir.config_parameter'].sudo().get_param('sms.endpoint', DEFAULT_ENDPOINT) + '/iap/sms/1/send'
        #TODO PRO, the default timeout is 15, do we have to increase it ?
        return iap.jsonrpc(endpoint, params=params)

    @api.model
    def _send_sms(self, numbers, message):
        """ Send sms using IAP
            :param numbers: List of numbers to which the message must be sent
            :param message: Message to send
        """
        account = self.env['iap.account'].get('sms')
        params = {
            'account_token': account.account_token,
            'numbers': numbers,
            'message': message,
        }
        endpoint = self.env['ir.config_parameter'].sudo().get_param('sms.endpoint', DEFAULT_ENDPOINT)
        iap.jsonrpc(endpoint + '/iap/message_send', params=params)
        return True
