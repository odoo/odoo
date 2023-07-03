# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests

from odoo.addons.pos_paytm import utils as paytm_utils
from odoo.exceptions import UserError, ValidationError
from odoo import fields, models, api, _
from datetime import datetime
from dateutil import tz

_logger = logging.getLogger(__name__)

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    paytm_tid = fields.Char(string='PayTM Terminal ID')
    channel_id = fields.Char(string='PayTM Channel ID', default='EDC')
    accept_payment = fields.Selection(selection=[('auto', 'Automatically'), ('manual', 'Manually')], default='auto')
    allowed_payment_modes = fields.Selection(selection=[('all', 'All'), ('card', 'Card'), ('qr', 'QR')], default='all')

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('paytm', 'PayTM')]

    def _get_paytm_payment_provider(self):
        paytm_payment_provider = self.env['payment.provider'].search([('code', '=', 'paytm')], limit=1)

        if not paytm_payment_provider:
            raise UserError(_("PayTM payment provider is missing"))

        return paytm_payment_provider

    def _paytm_make_request(self, url, payload=None):
        """ Make a request to PayTM API.

        :param str url: The url to be reached by the request.
        :param dict payload: The payload of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        """
        try:
            paytm_payment_provider = self._get_paytm_payment_provider()
            if paytm_payment_provider.state == 'test':
                api_url = 'https://securegw-stage.paytm.in/ecr/'
            else: 
                api_url = 'https://securegw-edc.paytm.in/ecr/'
            response = requests.post(api_url+url, json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            _logger.warning("Cannot connect with PayTM")
            return {'body':{'resultInfo': {'resultCode': "F", "resultMsg": _("Unable to establish connection with PayTM.")}}}
        return response.json()

    def paytm_make_payment_request(self, amount, transaction, timestamp):
        body = self._paytm_get_request_body(transaction, timestamp)
        body['transactionAmount'] = str(int(amount))
        if self.accept_payment == 'auto':
            body['autoAccept'] = 'True'
        body['paymentMode'] = self.allowed_payment_modes.upper()
        head = self._paytm_get_request_head(body)
        merchantExtendedInfo = {'paymentMode': self.allowed_payment_modes.upper()}
        if self.accept_payment == 'auto':
            merchantExtendedInfo['autoAccept'] = 'True'
        body['merchantExtendedInfo'] = merchantExtendedInfo
        payload = {'head': head, 'body': body}
        response = self._paytm_make_request('payment/request', payload=payload)
        return response

    def paytm_fetch_payment_status(self, transaction, timestamp):
        body = self._paytm_get_request_body(transaction, timestamp)
        head = self._paytm_get_request_head(body)
        payload = {'head': head, 'body': body}
        response = self._paytm_make_request('V2/payment/status', payload=payload)
        return response

    def _paytm_get_request_body(self, transaction, timestamp):
        paytm_payment_provider = self._get_paytm_payment_provider()
        if paytm_payment_provider.state == 'disabled':
            raise UserError('PayTM payment provider is disabled.')
        time = datetime.fromtimestamp(timestamp).astimezone(tz=tz.gettz('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M:%S")
        return {
            'paytmMid': paytm_payment_provider.paytm_mid,
            'paytmTid': self.paytm_tid,
            'transactionDateTime': time,
            'merchantTransactionId': transaction,
        }

    def _paytm_get_request_head(self, body):
        paytm_payment_provider = self._get_paytm_payment_provider()
        return {
            'requestTimeStamp' : body["transactionDateTime"],
            'channelId' : self.channel_id,
            'checksum' : paytm_utils.generate_signature(body, paytm_payment_provider.merchant_key),
        }

    @api.constrains('use_payment_terminal')
    def _check_paytm_terminal(self):
        for record in self:
            if record.use_payment_terminal == 'paytm' and record.company_id.currency_id.name != 'INR':
                raise UserError('This Payment Terminal is only valid for INR Currency')

    def action_paytm_key(self):
        res_id = self._get_paytm_payment_provider().id
        # Redirect
        return {
            'name': _('PayTM'),
            'res_model': 'payment.provider',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': res_id,
        }
