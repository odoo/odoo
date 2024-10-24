# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import requests
import uuid

from datetime import timedelta
from hashlib import sha1
from urllib.parse import urlencode, urljoin

from odoo import _, fields, models
from odoo.exceptions import RedirectWarning, ValidationError

from odoo.addons.payment_razorpay import const
from odoo.addons.payment_razorpay_oauth.const import OAUTH_URL

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    razorpay_key_id = fields.Char(required_if_provider=False)
    razorpay_key_secret = fields.Char(required_if_provider=False)
    razorpay_webhook_secret = fields.Char(required_if_provider=False)

    # Oauth fields
    razorpay_access_token = fields.Char(
        string="Razorpay Access Token",
        groups='base.group_system',
        copy=False,
    )
    razorpay_access_token_expiration = fields.Datetime(
        string="Razorpay Access Token Expiration",
        groups='base.group_system',
        copy=False,
    )
    razorpay_account_id = fields.Char(
        string="Razorpay Account ID",
        groups='base.group_system',
        copy=False,
    )
    razorpay_refresh_token = fields.Char(
        string="Razorpay Refresh Token",
        groups='base.group_system',
        copy=False,
    )
    razorpay_public_token = fields.Char(
        string="Razorpay Public Token",
        groups='base.group_system',
        copy=False,
    )

    # === ACTION METHODS ===#

    def action_razorpay_redirect_to_oauth_url(self):
        """ Redirect to the Razorpay Oauth url.

        :return: A url action with Razorpay Oauth url.
        :rtype: dict
        """
        self.ensure_one()
        if self.env.company.currency_id.name not in const.SUPPORTED_CURRENCIES:
            raise RedirectWarning(
                _(
                    "Razorpay is not available in your country, please use another payment"
                    " provider."
                ),
                self.env.ref('payment.action_payment_provider').id,
                _("Other Payment Providers"),
            )
        params = {
            'state': self._razorpay_generate_authorization_state(),
            'redirect_uri': self.get_base_url() + '/payment/razorpay/oauth/callback',
        }
        authorization_url = urljoin(OAUTH_URL, 'authorize?%s' % urlencode(params))
        return {
            'type': 'ir.actions.act_url',
            'url': authorization_url,
            'target': 'self',
        }

    def action_razorpay_create_webhook(self):
        """ Create the Razorpay webhook for this payment provider.
        This method ensures that a webhook is correctly configured on Razorpay's side to sync
        payment events (such as successful payments or failures) with Odoo. It generates the
        necessary webhook details and sends them to the Razorpay API. If successful, a notification
        will be displayed in Odoo to confirm the update.

        :return: A notification message indicating that the webhook has been successfully updated,
                 followed by a soft reload of the current page.
        :rtype: dict
        """
        self.ensure_one()
        self._razorpay_generate_webhook()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("Webhook successfully generated"),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    def action_razorpay_revoked_token(self):
        """ Revoke the Razorpay access token and disconnect the account.
        This method clears the stored Razorpay credentials (such as access token, refresh token,
        account ID, and webhook secret) and updates the payment provider's state to 'disabled'.
        Once this method is executed, the Razorpay access token will no longer be valid,
        effectively disconnecting the Odoo instance from the associated Razorpay account.

        :return: A notification message confirming the disconnection.
        :rtype: str
        """
        self.ensure_one()
        self.write({
            'razorpay_account_id': False,
            'razorpay_webhook_secret': False,
            'razorpay_public_token': False,
            'razorpay_access_token': False,
            'state': 'disabled',
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'message': _("Successfully disconnected"),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    # === BUSINESS METHODS ===#

    def _razorpay_generate_authorization_state(self):
        """ Generate a unique string to be used as the state parameter during Razorpay OAuth
        authorization with Razorpay provider id as prefix.

        :return: Unique string.
        :rtype: str
        """
        database_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        current_date = fields.Datetime.now()
        # Prefix the generated string with the provider's ID, which can be split later in the
        # callback to retrieve the provider ID from state.
        return f'{self.id}-' + sha1(f'{database_uuid}{current_date}'.encode()).hexdigest()

    def _razorpay_generate_webhook(self):
        """ Generate Razorpay webhook. """
        webhook_secret = uuid.uuid4().hex
        payload = {
            'alert_email': self.env.user.partner_id.email,
            'events': const.HANDLED_WEBHOOK_EVENTS,
            'url': self.get_base_url() + '/payment/razorpay/webhook',
            'secret': webhook_secret,
        }
        _logger.info(
            "Sending create webhook request for account %s:\n%s",
            self.razorpay_account_id, pprint.pformat(payload)
        )
        webhook_data = self.with_context(razorpay_api_version='v2')._razorpay_make_request(
            f'accounts/{self.razorpay_account_id}/webhooks',
            payload=payload,
        )
        self.razorpay_webhook_secret = webhook_secret
        _logger.info(
            "Response of create webhook request for account %s:\n%s",
            self.razorpay_account_id, pprint.pformat(webhook_data)
        )

    def _razorpay_get_access_token(self):
        # OVERRIDE
        if not self.razorpay_account_id:
            return super()._razorpay_get_access_token()
        # Check if the access token is expired, refresh it if necessary
        if self.razorpay_access_token_expiration <= fields.Datetime.now():
            self._razorpay_refresh_token()
        return self.razorpay_access_token

    def _razorpay_get_public_token(self):
        # OVERRIDE
        self.ensure_one()
        return self.razorpay_public_token

    def _razorpay_refresh_token(self):
        """ Refresh the Razorpay access token.
        This method retrieves a new access token using the refresh token and updates the record
        with the new token details. It handles errors if the token cannot be refreshed.

        :return: dict
        """
        self.ensure_one()
        params = {
            'refresh_token': self.razorpay_refresh_token,
        }
        response = self._razorpay_make_proxy_request('get_refresh_token', params=params)
        if response.get('access_token'):
            expires_in = fields.Datetime.now() + timedelta(seconds=int(response['expires_in']))
            self.write({
                'razorpay_access_token': response['access_token'],
                'razorpay_public_token': response['public_token'],
                'razorpay_access_token_expiration': expires_in,
                'razorpay_refresh_token': response['refresh_token'],
            })

    def _razorpay_make_proxy_request(self, endpoint, params=None, timeout=60):
        """ Make a request to the Razorpay proxy at the specified endpoint.

        :param str endpoint: The proxy endpoint to be reached by the request
        :param dict payload: The payload of the request
        :param int version: The proxy version used
        :return The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """
        proxy_payload = {
            'jsonrpc': '2.0',
            'id': uuid.uuid4().hex,
            'method': 'call',
            'params': params,
        }
        url = urljoin(OAUTH_URL, endpoint)
        try:
            response = requests.post(url, json=proxy_payload, timeout=timeout)
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable To Reach Endpoint At %s", url)
            raise ValidationError("Razorpay Proxy: " + _("Could not establish the connection."))
        except requests.exceptions.HTTPError:
            _logger.exception("Invalid API request at %s with data %s", url, pprint.pformat(params))
            raise ValidationError(
                "Razorpay Proxy: " + _("An error occurred when communicating with the proxy.")
            )

        response = response.json()
        if response.get('error'):
            error_message = response['error'].get('data', {}).get(
                'message', response['error'].get('description', '')
            )
            _logger.exception("Request forwarded with error: %s", error_message)
            raise ValidationError("Razorpay: " + _("%(error)s", error_message))

        return response.get('result', {})
