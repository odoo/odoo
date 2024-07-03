import logging
import requests

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
TIMEOUT = 10


class PosPaymentProvider(models.Model):
    _inherit = 'pos.payment.provider'

    code = fields.Selection(selection_add=[('viva_wallet', 'Viva Wallet')], ondelete={'viva_wallet': 'set default'})
    viva_wallet_merchant_id = fields.Char(
        string='Merchant ID',
        help='Used when connecting to Viva Wallet: https://developer.vivawallet.com/getting-started/find-your-account-credentials/merchant-id-and-api-key/',
        copy=False)
    viva_wallet_api_key = fields.Char(
        string='API Key',
        help='Used when connecting to Viva Wallet: https://developer.vivawallet.com/getting-started/find-your-account-credentials/merchant-id-and-api-key/',
        copy=False)
    viva_wallet_client_id = fields.Char(
        string='Client ID',
        help='Used when connecting to Viva Wallet: https://developer.vivawallet.com/getting-started/find-your-account-credentials/pos-apis-credentials/#find-your-pos-apis-credentials',
        copy=False)
    viva_wallet_client_secret = fields.Char(string='Client secret', copy=False)
    viva_wallet_bearer_token = fields.Char(default='Bearer Token', copy=False)
    viva_wallet_webhook_verification_key = fields.Char(copy=False)
    viva_wallet_webhook_endpoint = fields.Char(compute='_compute_viva_wallet_webhook_endpoint', readonly=True)

    @api.constrains('code', 'mode')
    def _check_viva_wallet_credentials(self):
        for record in self:
            if (record.code == 'viva_wallet'
                and record.mode != 'disabled'
                and not all(record[f] for f in [
                    'viva_wallet_merchant_id',
                    'viva_wallet_api_key',
                    'viva_wallet_client_id',
                    'viva_wallet_client_secret']
                )
            ):
                raise UserError(_('It is essential to provide API key for the use of viva wallet'))

    def _compute_viva_wallet_webhook_endpoint(self):
        web_base_url = self.get_base_url()
        self.viva_wallet_webhook_endpoint = f"{web_base_url}/pos_viva_wallet/notification?company_id={self.company_id.id}&token={self.viva_wallet_webhook_verification_key}"

    def write(self, vals):
        record = super().write(vals)
        if vals.get('viva_wallet_merchant_id') and vals.get('viva_wallet_api_key'):
            self.viva_wallet_webhook_verification_key = self._get_verification_key(
                self._viva_wallet_webhook_get_endpoint(),
                self.viva_wallet_merchant_id,
                self.viva_wallet_api_key
                )
            if not self.viva_wallet_webhook_verification_key:
                raise UserError(_("Can't update payment Provider. Please check the data and update it."))
        return record

    def create(self, vals):
        records = super().create(vals)
        for record in records:
            if record.viva_wallet_merchant_id and record.viva_wallet_api_key:
                record.viva_wallet_webhook_verification_key = record._get_verification_key(
                    record._viva_wallet_webhook_get_endpoint(),
                    record.viva_wallet_merchant_id,
                    record.viva_wallet_api_key,
                )
                if not record.viva_wallet_webhook_verification_key:
                    raise UserError(_("Can't create payment provider. Please check the data and update it."))
        return records

    def _get_verification_key(self, endpoint, viva_wallet_merchant_id, viva_wallet_api_key):
        # Get a key to configure the webhook.
        # this key need to be the response when we receive a notifiaction
        # do not execute this query in test mode
        if tools.config['test_enable']:
            return 'viva_wallet_test'

        auth = requests.auth.HTTPBasicAuth(viva_wallet_merchant_id, viva_wallet_api_key)
        try:
            resp = requests.get(f"{endpoint}/api/messages/config/token", auth=auth, timeout=TIMEOUT)
        except requests.exceptions.RequestException:
            _logger.exception('Failed to call https://%s/api/messages/config/token endpoint', endpoint)
        return resp.json().get('Key')

    def _viva_wallet_webhook_get_endpoint(self):
        if self.mode == 'test':
            return 'https://demo.vivapayments.com'
        return 'https://www.vivapayments.com'
