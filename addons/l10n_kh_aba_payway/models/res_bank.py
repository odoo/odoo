import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime
from urllib.parse import urljoin

import requests

from odoo import _, api, fields, models,modules
from odoo.exceptions import ValidationError, UserError
from odoo.tools import config

from .. import const

MAX_RETRY = 2

_logger = logging.getLogger(__name__)


def _make_payway_api_request(base_url: str, endpoint: str, payload: dict):

    if config['test_enable'] or modules.module.current_test:
        raise UserError(_("Transaction is blocked during tests."))

    url = urljoin(base_url, endpoint)
    headers = {"Content-Type": "application/json"}

    # Retry 2 more time
    for attempt in range(MAX_RETRY + 1):
        try:
            response = requests.post(
                url, headers=headers, data=json.dumps(payload), verify=True
            )

            if response.status_code != 200:
                response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as err:
            _logger.error("PayWay API HTTP Error: %s", err)
            # Handle HTTP Exception from API
            if attempt == MAX_RETRY:
                return response.json()

            continue

        except (requests.RequestException, ValueError) as err:
            if attempt == MAX_RETRY:
                raise ValidationError(
                    _("Could not establish a connection to PayWay API. Error: %s", err)
                )
            continue

    raise ValidationError(_("Could not establish a connection to PayWay API."))


class ResBank(models.Model):
    _inherit = "res.partner.bank"

    production_payway_merchant_id = fields.Char(
        string='Merchant ID',
        help="Enter your production PayWay Merchant ID. You'll receive this by email after obtaining a Go Live approval from ABA PayWay.",
    )
    production_payway_key = fields.Char(
        string='API Key',
        help="Enter your production PayWay API Key. You'll receive this by email after obtaining a Go Live approval from ABA PayWay.",
        groups='base.group_system',
    )

    sandbox_payway_merchant_id = fields.Char(
        string='Merchant ID',
        help='Enter your unique PayWay Merchant ID. You can find it in the email registered for your PayWay Sandbox account.',
    )
    sandbox_payway_key = fields.Char(
        string='API Key',
        help='Enter your unique PayWay API Key. You can find it in the email registered for your PayWay Sandbox account.',
        groups='base.group_system',
    )

    payway_environment = fields.Selection(
        [('disable', 'Disable'), ('production', 'Production'), ('sandbox', 'Sandbox')],
        string='Environment',
        default='disable',
        required=True,
        help='Switch between Sandbox and Production payment environments for ABA PayWay.',
    )

    digital_qr_lifetime = fields.Integer(
        string='QR on screen expire time (minute)',
        default=3,
        required=True,
    )

    bill_qr_lifetime = fields.Integer(
        string='QR on Bill expire time (Minute)',
        default=10,
        required=True,
    )

    @api.constrains('digital_qr_lifetime', 'bill_qr_lifetime')
    def _check_qr_lifetimes(self):
        for record in self:
            if not isinstance(record.digital_qr_lifetime, int) or record.digital_qr_lifetime < 1:
                raise ValidationError("QR on screen expire time must be an integer and at least 1 minute.")
            if not isinstance(record.bill_qr_lifetime, int) or record.bill_qr_lifetime < 1:
                raise ValidationError("QR on Bill expire time must be an integer and at least 1 minute.")

            if record.digital_qr_lifetime > 43200 or record.bill_qr_lifetime > 43200:
                raise ValidationError("QR expire time must not be greater than 30 Days.")

    @api.model
    def _get_available_qr_methods(self):
        """Extend the base list of QR methods."""
        res = super()._get_available_qr_methods()
        res.append(('abapay_khqr', _("ABA KHQR"), 10))
        res.append(('wechat', _("WeChat Pay"), 10))
        res.append(('alipay', _("Alipay"), 10))
        return res

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        # Raise error msg

        if self.sudo().payway_environment == 'disable':
            return _("ABA PayWay is currently disabled. Please select an environment to proceed.")

        if currency.name not in ['USD', 'KHR']:
            return _("This payment method only supports transactions in USD or KHR currency.\nTo continue, please update your store currency and try again.")

        if self.sudo().payway_environment == 'production':
            if not self.sudo().production_payway_merchant_id:
                return _("For Production environment, the 'PayWay Merchant ID' is required.")
            if not self.sudo().production_payway_key:
                return _("For Production environment, the 'PayWay API Key' is required.")

        elif self.sudo().payway_environment == 'sandbox':
            if not self.sudo().sandbox_payway_merchant_id:
                return _("For Sandbox environment, the 'PayWay Merchant ID' is required.")
            if not self.sudo().sandbox_payway_key:
                return _("For Sandbox environment, the 'PayWay API Key' is required.")

        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):

        if qr_method in const.PAYMENT_METHODS_CODES:

            model = self.env.context.get('model')
            qr_type = self.env.context.get('qr_type')
            qr_tran_id = self.env.context.get('qr_tran_id') or ""

            api_url, merchant_id, api_key = self._payway_get_api_cred()
            # Why close before creating new one?
            self._payway_api_close_transaction(qr_tran_id)

            base_odoo_url: str = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_odoo_url = (
                base_odoo_url.replace('http://', 'https://', 1)
                if base_odoo_url and base_odoo_url.startswith('http://') else base_odoo_url
            )
            webhook_url = urljoin(base_odoo_url, const.WEB_HOOK_PATH['pos']) if model == 'pos.order' else ''

            payload = {
                'req_time': datetime.now().strftime("%Y%m%d%H%M%S"),
                'merchant_id': merchant_id,
                'tran_id': qr_tran_id,
                'email': self.partner_id.email,
                'phone': self.partner_id.phone,
                'amount': amount,
                'payment_option': qr_method,
                'currency': currency.name.upper(),
                'lifetime': (
                    self.bill_qr_lifetime
                    if qr_type == const.POS_ORDER_QR_TYPE['bill'] else
                    self.digital_qr_lifetime
                ),
                'qr_image_template': (
                    'template2' if model == 'pos.order' and
                    qr_type == const.POS_ORDER_QR_TYPE['bill'] else 'template1_color'
                ),
                'callback_url': base64.b64encode(webhook_url.encode('utf-8')).decode(
                    'utf-8'
                ),
            }
            payload.update(
                {'hash': self._payway_calculate_payment_secure_hash(api_key, payload)}
            )

            return api_url, payload

        return super()._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_generation_params(
        self,
        qr_method,
        amount,
        currency,
        debtor_partner,
        free_communication,
        structured_communication,
    ):

        if qr_method in const.PAYMENT_METHODS_CODES:

            api_url, payload = self._get_qr_vals(
                qr_method,
                amount,
                currency,
                debtor_partner,
                free_communication,
                structured_communication,
            )

            response = _make_payway_api_request(
                api_url, '/api/payment-gateway/v1/payments/generate-qr', payload
            )

            if str(response['status']['code']) != '0':
                # Payway return error
                raise ValidationError(response['status']['message'])

            return {
                'barcode_type': 'QR',
                'width': 150,
                'height': 150,
                'value': response['qrString'],
            }

        return super()._get_qr_code_generation_params(
            qr_method,
            amount,
            currency,
            debtor_partner,
            free_communication,
            structured_communication,
        )

    def _get_qr_code_base64(
        self,
        qr_method,
        amount,
        currency,
        debtor_partner,
        free_communication,
        structured_communication,
    ):

        return super()._get_qr_code_base64(
            qr_method,
            amount,
            currency,
            debtor_partner,
            free_communication,
            structured_communication,
        )

    def _payway_api_close_transaction(self, qr_tran_id: str):
        """Close payway transaction.

        :return: transaction id.
        :rtype: reponse dict
        """

        api_url, merchant_id, api_key = self._payway_get_api_cred()
        payload = {
            'req_time': datetime.now().strftime("%Y%m%d%H%M%S"),
            'merchant_id': merchant_id,
            'tran_id': qr_tran_id,
        }
        payload.update(
            {'hash': self._payway_calculate_check_txn_secure_hash(api_key, payload)}
        )
        response = _make_payway_api_request(
            api_url, '/api/payment-gateway/v1/payments/close-transaction', payload
        )

        if (
            str(response['status']['code']) == '00'
            or str(response['status']['code']) == '5'
        ):
            # Success or Transaction no found
            return response

        raise ValidationError(response['status']['message'])

    def _payway_api_check_transaction(self, qr_tran_id: str):
        """Check payway transaction.

        :return: transaction id.
        :rtype: reponse dict
        """
        api_url, merchant_id, api_key = self._payway_get_api_cred()
        payload = {
            'req_time': datetime.now().strftime("%Y%m%d%H%M%S"),
            'merchant_id': merchant_id,
            'tran_id': qr_tran_id,
        }
        payload.update(
            {'hash': self._payway_calculate_check_txn_secure_hash(api_key, payload)}
        )
        response = _make_payway_api_request(
            api_url, '/api/payment-gateway/v1/payments/check-transaction-2', payload
        )

        if str(response['status']['code']) == '00':
            return response

        raise ValidationError(response['status']['message'])

    def _payway_get_api_cred(self):
        """Return the URL of the API corresponding to the selected payway environment.

        :return: (API URL, Merchant ID, API Key).
        :rtype: (str, str, str)
        """

        self.ensure_one()
        if self.payway_environment == 'production':
            api_url = const.API_URLS['production']
            return (
                api_url,
                self.production_payway_merchant_id,
                self.production_payway_key,
            )
        elif self.payway_environment == 'sandbox':
            api_url = const.API_URLS['sandbox']
            return (
                api_url,
                self.sandbox_payway_merchant_id,
                self.sandbox_payway_key,
            )
        raise ValidationError(_("ABA PayWay is disabled."))

    def _payway_calculate_payment_secure_hash(self, api_key: str, payload: dict):
        """Compute the secure hash for the provided data according to the PayWay documentation.

        :param dict data: The data to hash.
        :return: The calculated hash.
        :rtype: str
        """

        secure_hash_keys = const.PAYMENT_SECURE_HASH_KEYS
        data_to_sign = [str(payload.get(k, '')) for k in secure_hash_keys]
        signing_string = ''.join(data_to_sign)
        hmac_hash = hmac.new(
            api_key.encode(), signing_string.encode(), hashlib.sha512
        ).digest()
        base64_encoded = base64.b64encode(hmac_hash).decode()
        return base64_encoded

    def _payway_calculate_check_txn_secure_hash(self, api_key: str, payload: dict):
        """Compute the secure hash for the provided data according to the PayWay documentation for checking transaction.

        :param dict data: The data to hash.
        :return: The calculated hash.
        :rtype: str
        """
        secure_hash_keys = const.CHECK_TXN_SECURE_HASH_KEYS
        data_to_sign = [str(payload[k]) for k in secure_hash_keys]
        signing_string = ''.join(data_to_sign)
        hmac_hash = hmac.new(
            api_key.encode(), signing_string.encode(), hashlib.sha512
        ).digest()
        base64_encoded = base64.b64encode(hmac_hash).decode()
        return base64_encoded
