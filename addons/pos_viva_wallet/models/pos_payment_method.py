# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests

from odoo import fields, models, _
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)
TIMEOUT = 10


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('viva_wallet', 'Viva Wallet')]

    viva_wallet_latest_response = fields.Json()  # used to buffer the latest asynchronous notification from Adyen.

    def _viva_wallet_account_get_endpoint(self):
        if self.pos_payment_provider_id.mode == 'test':
            return 'https://demo-accounts.vivapayments.com'
        return 'https://accounts.vivapayments.com'

    def _viva_wallet_api_get_endpoint(self):
        if self.pos_payment_provider_id.mode == 'test':
            return 'https://demo-api.vivapayments.com'
        return 'https://api.vivapayments.com'

    def _is_write_forbidden(self, fields):
        # Allow the modification of these fields even if a pos_session is open
        whitelisted_fields = {'viva_wallet_latest_response'}
        return super(PosPaymentMethod, self)._is_write_forbidden(fields - whitelisted_fields)

    def _bearer_token(self, session):
        self.ensure_one()

        data = {'grant_type': 'client_credentials'}
        auth = requests.auth.HTTPBasicAuth(self.pos_payment_provider_id.viva_wallet_client_id, self.pos_payment_provider_id.viva_wallet_client_secret)
        try:
            resp = session.post(f"{self._viva_wallet_account_get_endpoint()}/connect/token", auth=auth, data=data, timeout=TIMEOUT)
        except requests.exceptions.RequestException:
            _logger.exception("Failed to call viva_wallet_bearer_token endpoint")

        access_token = resp.json().get('access_token')
        if access_token:
            self.pos_payment_provider_id.viva_wallet_bearer_token = access_token
            return {'Authorization': f"Bearer {access_token}"}
        else:
            raise UserError(_('Not receive Bearer Token'))

    def _call_viva_wallet(self, endpoint, action, data=None):
        session = get_viva_wallet_session()
        session.headers.update({'Authorization': f"Bearer {self.pos_payment_provider_id.viva_wallet_bearer_token}"})
        endpoint = f"{self._viva_wallet_api_get_endpoint()}/ecr/v1/{endpoint}"
        try:
            resp = session.request(action, endpoint, json=data, timeout=TIMEOUT)
        except requests.exceptions.RequestException as e:
            return {'error': _("There are some issues between us and Viva Wallet, try again later.%s)", e)}

        if resp.text and resp.json().get('detail') == 'Could not validate credentials':
            session.headers.update(self._bearer_token(session))
            resp = session.request(action, endpoint, json=data, timeout=TIMEOUT)

        if resp.status_code == 200:
            if resp.text:
                return resp.json()
            return {'success': resp.status_code}
        else:
            return {'error': _("There are some issues between us and Viva Wallet, try again later. %s", resp.json().get('detail'))}

    def _retrieve_session_id(self, data_webhook):
        # Send a request to confirm the status of the sesions_id
        # Need wait to the status of sesions_id is updated setted in session headers; code 202

        MerchantTrns = data_webhook.get('MerchantTrns')
        if not MerchantTrns:
            self._send_notification(
                {'error': _(
                    "Your transaction with Viva Wallet failed. Please try again later."
                    )}
                )
        session_id, pos_session_id = MerchantTrns.split("/")  # Split to retrieve pos_sessions_id
        endpoint = f"sessions/{session_id}"
        data = self._call_viva_wallet(endpoint, 'get')

        if data.get('success'):
            data.update({'pos_session_id': pos_session_id, 'data_webhook': data_webhook})
            self.viva_wallet_latest_response = data
            self._send_notification(data)
        else:
            self._send_notification(
                {'error': _(
                    "There are some issues between us and Viva Wallet, try again later. %s",
                    data.get('detail')
                    )}
                )

    def _send_notification(self, data):
        # Send a notification to the point of sale channel to indicate that the transaction are finish
        pos_session_sudo = self.env["pos.session"].browse(int(data.get('pos_session_id', False)))
        if pos_session_sudo:
            pos_session_sudo.config_id._notify('VIVA_WALLET_LATEST_RESPONSE', {
                'config_id': pos_session_sudo.config_id.id
            })

    def viva_wallet_send_payment_request(self, data):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Only 'group_pos_user' are allowed to fetch token from Viva Wallet"))

        endpoint = "transactions:sale"
        return self._call_viva_wallet(endpoint, 'post', data)

    def viva_wallet_send_payment_cancel(self, data):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Only 'group_pos_user' are allowed to fetch token from Viva Wallet"))

        session_id = data.get('sessionId')
        cash_register_id = data.get('cashRegisterId')
        endpoint = f"sessions/{session_id}?cashRegisterId={cash_register_id}"
        return self._call_viva_wallet(endpoint, 'delete')

    def get_latest_viva_wallet_status(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Only 'group_pos_user' are allowed to get latest transaction status"))

        self.ensure_one()
        latest_response = self.sudo().viva_wallet_latest_response
        return latest_response


def get_viva_wallet_session():
    session = requests.Session()
    session.mount('https://', requests.adapters.HTTPAdapter(max_retries=requests.adapters.Retry(
        total=6,
        backoff_factor=2,
        status_forcelist=[202, 500, 502, 503, 504],
        )))
    return session
