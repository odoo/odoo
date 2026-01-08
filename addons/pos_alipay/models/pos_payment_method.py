# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests
import time
import json
import urllib.parse

from odoo import fields, models, _
from odoo.exceptions import UserError, AccessError, AccessDenied

from odoo.addons.pos_alipay import utils

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('alipay', 'Alipay')]

    # Alipay
    alipay_client_id = fields.Char(string='Alipay Merchant ID', help='Your Alipay merchant ID', copy=False)
    alipay_location = fields.Selection([
        ("na", "North America"),
        ("sea", "Asia"),
        ("eu", "Europe")
    ], string="Alipay Location", default="na", help="The location of your Alipay account")
    alipay_private_key = fields.Char(string="Alipay Private Key", help="Your Alipay private key", copy=False)

    alipay_latest_response = fields.Char(copy=False, groups='base.group_erp_manager')  # used to buffer the latest asynchronous notification from Alipay.

    def _alipay_api_get_endpoint(self):
        return "https://open-%s-global.alipay.com" % self.alipay_location

    def _is_write_forbidden(self, fields):
        return super(PosPaymentMethod, self)._is_write_forbidden(fields - {'alipay_latest_response'})

    def get_latest_alipay_status(self):
        self.ensure_one()
        if not self.env.su and not self.user_has_groups('point_of_sale.group_pos_user'):
            raise AccessDenied()

        latest_response = self.sudo().alipay_latest_response
        latest_response = json.loads(latest_response) if latest_response else False
        return latest_response

    def _alipay_api_get_headers(self, url, data):
        request_time = str(round(time.time() * 1000))
        signature = utils.sign("POST", url, self.alipay_client_id,
                               request_time, json.dumps(data), self.alipay_private_key)
        headers = {
            "signature": "algorithm=RSA256, keyVersion=1, signature=%s" % signature,
            "Content-Type": "application/json; charset=UTF-8",
            "client-id": self.alipay_client_id,
            "request-time": request_time
        }
        return headers

    def proxy_alipay_request(self, data, operation=False):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Do not have access to send payment request to Alipay"))

        if operation == "pay":
            return self._alipay_create_payment_request(data)
        elif operation == "query":
            return self._alipay_query_payment_request(data)
        elif operation == "cancel":
            return self._alipay_cancel_payment_request(data)
        elif operation == "refund":
            return self._alipay_refund_payment_request(data)

    def _alipay_create_payment_request(self, data):
        url = "/ams/api/v1/payments/pay"
        endpoint = urllib.parse.urljoin(self._alipay_api_get_endpoint(), url)
        payload = data
        payload["order"]["merchant"]["merchantMCC"] = "5812"
        payload["order"]["merchant"]["store"]["storeMCC"] = "5812"

        headers = self._alipay_api_get_headers(url, payload)
        try:
            res = requests.post(endpoint, json=payload, headers=headers)
            data = res.json()
            return data
        except requests.exceptions.RequestException:
            _logger.exception("Failed to call Aipay API endpoint")
            raise UserError(_("There are some problems with the Alipay API endpoint. Please try again later."))

    def _alipay_query_payment_request(self, data):
        url = "/ams/api/v1/payments/inquiryPayment"
        endpoint = urllib.parse.urljoin(self._alipay_api_get_endpoint(), url)
        payload = data

        headers = self._alipay_api_get_headers(url, payload)
        try:
            res = requests.post(endpoint, json=payload, headers=headers)
            data = res.json()
            return data
        except requests.exceptions.RequestException:
            _logger.exception("Failed to call Aipay API endpoint")
            raise UserError(_("There are some problems with the Alipay API endpoint. Please try again later."))

    def _alipay_cancel_payment_request(self, data):
        url = "/ams/api/v1/payments/cancel"
        endpoint = urllib.parse.urljoin(self._alipay_api_get_endpoint(), url)
        payload = data
        headers = self._alipay_api_get_headers(url, payload)
        try:
            res = requests.post(endpoint, json=payload, headers=headers)
            data = res.json()
            return data
        except requests.exceptions.RequestException:
            _logger.exception("Failed to call Aipay API endpoint")
            raise UserError(_("There are some problems with the Alipay API endpoint. Please try again later."))

    def _alipay_refund_payment_request(self, data):
        url = "/ams/api/v1/payments/refund"
        endpoint = urllib.parse.urljoin(self._alipay_api_get_endpoint(), url)
        payload = data
        headers = self._alipay_api_get_headers(url, payload)
        try:
            res = requests.post(endpoint, json=payload, headers=headers)
            data = res.json()
            return data
        except requests.exceptions.RequestException:
            _logger.exception("Failed to call Aipay API endpoint")
            raise UserError(_("There are some problems with the Alipay API endpoint. Please try again later."))
