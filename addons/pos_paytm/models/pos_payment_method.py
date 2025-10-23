# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import hashlib
import logging
import requests
import secrets
import string

from odoo.exceptions import UserError
from odoo import fields, models, api, _
from datetime import datetime
from dateutil import tz

_logger = logging.getLogger(__name__)
REQUEST_TIMEOUT = 30
iv = b'@@@@&&&&####$$$$'

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    paytm_tid = fields.Char(string='PayTM Terminal ID', help="Terminal model or Activation code \n ex: 70000123")
    channel_id = fields.Char(string='PayTM Channel ID', default='EDC')
    accept_payment = fields.Selection(selection=[('auto', 'Automatically'), ('manual', 'Manually')], default='auto', help="Choose accept payment mode: \n Manually or Automatically")
    allowed_payment_modes = fields.Selection(selection=[('all', 'All'), ('card', 'Card'), ('qr', 'QR')], default='all', help="Choose allow payment mode: \n All/Card or QR")
    paytm_mid = fields.Char(string="PayTM Merchant ID", help="Go to https://business.paytm.com/ and create the merchant account")
    paytm_merchant_key = fields.Char(string="PayTM Merchant API Key", help="Merchant/AES key \n ex: B1o6Ivjy8L1@abc9", groups='point_of_sale.group_pos_manager')
    paytm_test_mode = fields.Boolean(string="PayTM Test Mode", default=False, help="Turn it on when in Test Mode")

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('paytm', 'PayTM')]

    def _paytm_make_request(self, url, payload=None):
        """ Make a request to PayTM API.

        :param str url: The url to be reached by the request.
        :param dict payload: The payload of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        """
        try:
            if self.paytm_test_mode:
                api_url = 'https://securegw-stage.paytm.in/ecr/'
            else:
                api_url = 'https://securegw-edc.paytm.in/ecr/'
            response = requests.post(api_url+url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except (requests.exceptions.Timeout, requests.exceptions.RequestException) as error:
            _logger.warning("Cannot connect with PayTM. Error: %s", error)
            return {'error': '%s' % error}
        res_json = response.json()
        if res_json.get('body'):
            return res_json['body']
        default_error_msg = _('Something went wrong with paytm request. Please try later.')
        error = res_json.get('error') or default_error_msg
        return {'error': '%s' % error}

    def paytm_make_payment_request(self, amount, transaction_id, reference_id, timestamp):
        body = self._paytm_get_request_body(transaction_id, reference_id, timestamp)
        body['transactionAmount'] = str(int(amount))
        if self.accept_payment == 'auto':
            body['autoAccept'] = 'True'
        body['paymentMode'] = self.allowed_payment_modes.upper()
        head = self._paytm_get_request_head(body)
        head_error = head.get('error')
        if head_error:
            return {'error': '%s' % head_error}
        merchantExtendedInfo = {'paymentMode': self.allowed_payment_modes.upper()}
        if self.accept_payment == 'auto':
            merchantExtendedInfo['autoAccept'] = 'True'
        body['merchantExtendedInfo'] = merchantExtendedInfo
        payload = {'head': head, 'body': body}
        response = self._paytm_make_request('payment/request', payload=payload)
        result_code = response.get('resultInfo', {}).get('resultCode')
        if result_code == 'A':
            return response['resultInfo']
        elif result_code == 'F':
            return {'error': "%s" % response['resultInfo'].get('resultMsg', _('paytm transaction request declined'))}
        default_error_msg = _('makePaymentRequest expected resultCode not found in the response')
        error = response.get('error') or default_error_msg
        return {'error': '%s' % error}

    def paytm_fetch_payment_status(self, transaction_id, reference_id, timestamp):
        body = self._paytm_get_request_body(transaction_id, reference_id, timestamp)
        head = self._paytm_get_request_head(body)
        head_error = head.get('error') and head
        if head_error:
            return head_error
        payload = {'head': head, 'body': body}
        response = self._paytm_make_request('V2/payment/status', payload=payload)
        result_code = response.get('resultInfo', {}).get('resultCode')
        if result_code == 'S':
            # Since we don't want to send extra data on RPC call
            # Only sending essential data when the transaction is successful
            data = response['resultInfo']
            data.update({
                    'authCode': response.get('authCode'),
                    'issuerMaskCardNo': response.get('issuerMaskCardNo'),
                    'issuingBankName': response.get('issuingBankName'),
                    'payMethod': response.get('payMethod'),
                    'cardType': response.get('cardType'),
                    'cardScheme': response.get('cardScheme'),
                    'merchantReferenceNo': response.get('merchantReferenceNo'),
                    'merchantTransactionId': response.get('merchantTransactionId'),
                    'transactionDateTime': response.get('transactionDateTime'),
            })
            return data
        elif result_code == 'F':
            return {'error': "%s" % response['resultInfo'].get('resultMsg', _('paytm transaction failure'))}
        elif result_code == 'P':
            return response['resultInfo']
        default_error_msg = _('paymentFetchRequest expected resultCode not found in the response')
        error = response.get('error') or default_error_msg
        return {'error': '%s' % error}

    def _paytm_generate_signature(self, params_dict, key):
        params_list = []
        for k in sorted(params_dict.keys()):
            value = params_dict[k]
            if value is None or params_dict[k].lower() == "null":
                value = ""
            params_list.append(str(value))
        salt = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))
        params_list.append(salt)
        params_with_salt = '|'.join(params_list)
        hashed_params = hashlib.sha256(params_with_salt.encode())
        hashed_params_with_salt = hashed_params.hexdigest() + salt
        padding = 12 #the padding value is a constant
        padded_hashed_params_with_salt = bytes(hashed_params_with_salt + padding * chr(padding), 'utf-8')
        try:
            cipher = Cipher(algorithms.AES(key.encode()), modes.CBC(iv))
            encryptor = cipher.encryptor()
            encrypted_hashed_params = encryptor.update(padded_hashed_params_with_salt) + encryptor.finalize()
            return base64.b64encode(encrypted_hashed_params).decode("UTF-8")
        except ValueError as error:
            _logger.warning("Cannot generate PayTM signature. Error: %s", error)
            return {'error': '%s' % error}

    def _paytm_get_request_body(self, transaction_id, reference_id, timestamp):

        time = datetime.fromtimestamp(timestamp).astimezone(tz=tz.gettz('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M:%S")
        return {
            'paytmMid': self.paytm_mid,
            'paytmTid': self.paytm_tid,
            'transactionDateTime': time,
            'merchantTransactionId': transaction_id,
            'merchantReferenceNo': reference_id,
        }

    def _paytm_get_request_head(self, body):
        paytm_signature = self._paytm_generate_signature(body, self.sudo().paytm_merchant_key)
        error = isinstance(paytm_signature, dict) and paytm_signature.get('error')
        if error:
            return {'error': '%s' % error}
        return {
            'requestTimeStamp' : body["transactionDateTime"],
            'channelId' : self.channel_id,
            'checksum' : paytm_signature,
        }

    @api.constrains('use_payment_terminal')
    def _check_paytm_terminal(self):
        for record in self:
            if record.use_payment_terminal == 'paytm' and record.company_id.currency_id.name != 'INR':
                raise UserError(_('This Payment Terminal is only valid for INR Currency'))
