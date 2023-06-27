# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests

from odoo.addons.pos_paytm import utils as paytm_utils
from odoo.exceptions import UserError
from odoo import fields, models, api, _
from datetime import datetime
from dateutil import tz

_logger = logging.getLogger(__name__)

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    paytm_mid = fields.Char(string='PayTM Merchant ID')
    paytm_tid = fields.Char(string='PayTM Terminal ID')
    merchant_key = fields.Char(string='PayTM Merchant Key')
    channel_id = fields.Char(string='PayTM Channel ID', default='EDC')
    paytm_test_mode = fields.Boolean(string='Test Mode', help='Run transactions in the test environment.')
    accept_payment = fields.Selection(selection=[('auto', 'Automatically'), ('manual', 'Manually')], default='auto')
    allowed_payment_modes = fields.Selection(selection=[('all', 'All'), ('card', 'Card'), ('qr', 'QR')], default='all')

    def _get_payment_terminal_selection(self):
        selection = super()._get_payment_terminal_selection()
        selection += [('paytm', 'PayTM')]
        return selection

    def _paytm_make_request(self, url, payload=None):
        """ Make a request to PayTM API.

        Note: self.ensure_one()

        :param str url: The url to be reached by the request.
        :param dict payload: The payload of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        """
        self.ensure_one()
        try:
            response = requests.post(url, json=payload)
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
        api_url = 'https://securegw-stage.paytm.in/ecr/payment/request' if self.paytm_test_mode else 'https://securegw-edc.paytm.in/ecr/payment/request'
        response = self._paytm_make_request(api_url, payload=payload)
        return response

    def paytm_fetch_payment_status(self, transaction, timestamp):
        body = self._paytm_get_request_body(transaction, timestamp)
        head = self._paytm_get_request_head(body)
        payload = {'head': head, 'body': body}
        api_url = 'https://securegw-stage.paytm.in/ecr/V2/payment/status' if self.paytm_test_mode else 'https://securegw-edc.paytm.in/ecr/V2/payment/status'
        response = self._paytm_make_request(api_url, payload=payload)
        return response

    def _paytm_get_request_body(self, transaction, timestamp):
        time = datetime.fromtimestamp(timestamp)
        utc = time.replace(tzinfo=tz.gettz('UTC'))
        ist = utc.astimezone(tz.gettz('Asia/Kolkata'))
        time = ist.strftime("%Y-%m-%d %H:%M:%S")
        return {
            'paytmMid': self.paytm_mid,
            'paytmTid': self.paytm_tid,
            'transactionDateTime': time,
            'merchantTransactionId': transaction,
        }

    def _paytm_get_request_head(self, body):
        checksum = paytm_utils.generateSignature(body, self.merchant_key)
        return {
            'requestTimeStamp' : body["transactionDateTime"],
            'channelId' : self.channel_id,
            'checksum' : checksum,
        }

    @api.constrains('use_payment_terminal')
    def _check_paytm_terminal(self):
        for record in self:
            if record.use_payment_terminal == 'paytm' and record.company_id.currency_id.name != 'INR':
                raise UserError('This Payment Terminal is only valid for INR Currency')
