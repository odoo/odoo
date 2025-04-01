# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint
from datetime import timedelta

import requests
from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_paymob import const
from odoo.addons.payment_paymob.controllers.main import PaymobController


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('paymob', "Paymob")], ondelete={'paymob': 'set default'}
    )
    paymob_account_country_id = fields.Many2one(
        string="Paymob Country",
        help="The country of the Paymob account",
        comodel_name='res.country',
        compute='_compute_paymob_account_country',
        store=True,
        readonly=False,
        domain=f'[("code", "in", {list(const.PAYMOB_CONFIG.keys())})]',
    )
    paymob_public_key = fields.Char(string="Paymob Public Key", required_if_provider='paymob')
    paymob_secret_key = fields.Char(
        string="Paymob Secret Key",
        required_if_provider='paymob',
        groups='base.group_system',
    )
    paymob_hmac_key = fields.Char(string="Paymob HMAC Key", required_if_provider='paymob')
    paymob_api_key = fields.Char(string="Paymob API Key", required_if_provider='paymob')
    paymob_access_token = fields.Char(
        string="Paymob Access Token",
        help="The short-lived token used to access Paymob APIs",
        groups='base.group_system',
    )
    paymob_access_token_expiry = fields.Datetime(
        string="Paymob Access Token Expiry",
        help="The moment at which the access token becomes invalid.",
        default='1970-01-01',
        groups='base.group_system',
    )

    # ==== CONSTRAINT METHODS === #

    @api.constrains('available_currency_ids', 'state')
    def _limit_available_country_currency_ids(self):
        for provider in self.filtered(lambda p: p.code == 'paymob'):
            if len(provider.available_currency_ids) > 1 and provider.state != 'disabled':
                raise ValidationError(_("Only one currency can be selected by Paymob account."))

    # === COMPUTE METHODS === #

    @api.depends('available_currency_ids')
    def _compute_paymob_account_country(self):
        for provider in self.filtered(lambda p: p.code == 'paymob'):
            if len(provider.available_currency_ids) == 1:
                provider.paymob_account_country_id = self.env['res.country'].search(
                    [('code', '=', provider._get_country_from_currency())], limit=1)

    @api.onchange('paymob_account_country_id')
    def _onchange_paymob_account_country(self):
        for provider in self.filtered(lambda p: p.code == 'paymob'):
            provider.available_currency_ids = self.env['res.currency'].with_context(
                active_test=False,
            ).search([('name', '=', provider._get_paymob_account_currency())], limit=1)

    # === ACTION METHODS === #

    def action_sync_paymob_payment_methods(self):
        """ Synchronize the payment methods with the ones on the paymob portal, the integration_name
        needs to be set to be able to communicate with the `payment_method.code` when the intention
        is created.

        :return: None
        """
        base_url = self.get_base_url()
        redirect_url = urls.url_join(base_url, PaymobController._return_url)
        webhook_url = urls.url_join(base_url, PaymobController._webhook_url)
        endpoint = '/api/ecommerce/integrations'
        is_live = self.state == 'enabled'
        params = {
            'is_plugin': 'true',
            'page_size': 500,
            'is_deprecated': 'false',
            'is_standalone': 'false',
            'is_live': json.dumps(is_live),
        }
        self.paymob_access_token = None
        paymob_payment_methods = self._paymob_make_request(
            endpoint,
            params=params,
            method='GET',
            is_client_request=False,
        )['results']
        available_payment_method_codes = self.payment_method_ids.mapped('code')
        matched_payment_methods = list(filter(
            lambda pm: (
                const.PAYMOB_PAYMENT_METHODS_MAPPING.get(pm.get('gateway_type'))
                in available_payment_method_codes and not pm.get('integration_name') or not (
                    'apple' in pm.get('integration_name').lower() or
                    'google' in pm.get('integration_name').lower()
                )
            ),
            # Apple Pay and Google Pay not supported for now because we don't have mobile only
            # payment methods.
            paymob_payment_methods
        ))
        if not matched_payment_methods:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Payment methods not found"),
                    'message': _("No matching payment methods were found on your Paymob account"),
                }
            }
        for payment_method in matched_payment_methods:
            payment_method_code = const.PAYMOB_PAYMENT_METHODS_MAPPING[
                payment_method.get('gateway_type')
            ]
            if payment_method_code == 'card' and payment_method.get('installments'):
                installment_payment_method = self.env['payment.method'].search(
                    [('code', '=', 'installments')], limit=1
                )
                if not installment_payment_method:
                    continue
                payment_method_code = 'installments'
            live_tag = 'live' if is_live else 'test'
            data = {
                'integration_name': payment_method_code + live_tag,
                'transaction_processed_callback': webhook_url,
                'transaction_response_callback': redirect_url,
            }
            self._paymob_make_request(
                f'/api/ecommerce/integrations/{payment_method["id"]}',
                method='PUT',
                data=data,
                is_client_request=False
            )
        # If no error raised by _paymob_make_request
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _("Successfully synchronized with Paymob"),
                'message': _("Payment methods have been successfully set up!"),
            }
        }

    # === BUSINESS METHODS === #

    def _paymob_make_request(
        self, endpoint, data=None, method='POST', is_refresh_token_request=False,
        is_client_request=True, params=None,
    ):
        """ Make a request to Paymob API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict data: The string payload of the request.
        :param bool is_refresh_token_request: Whether the request is for refreshing the access
                                              token.
        :param bool is_client_request: Whether the request is a client request or a backend request,
                                       it will depend what auth will be sent the access token
                                       generated from the api_key or the secret_key.
        :return: The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        url = self._paymob_get_api_url() + endpoint
        auth = ''
        if not is_refresh_token_request and is_client_request:
            auth = payment_utils.get_normalized_field(self.paymob_secret_key)
        elif not is_refresh_token_request:
            auth = self._paymob_fetch_access_token()
        headers = {'Authorization': f'Bearer {auth}'}

        try:
            response = requests.request(
                method, url, headers=headers, params=params, json=data, timeout=10
            )
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                # Paymob errors https://developer.paymob.com/api/rest/reference/orders/v2/errors/
                _logger.exception(
                    "Invalid API request at %s with data:\n%s", url, pprint.pformat(data)
                )
                msg = response.text
                if "This field may not be blank" in msg:
                    missing_fields = ", ".join(json.loads(msg).get('billing_data', {}).keys())

                    raise ValidationError(_(
                        "%(provider)s The following fields must be filled: %(fields)s",
                        fields=missing_fields,
                        provider="Paymob:",
                    ))

                raise ValidationError(_(
                    "%(provider)s The communication with the API failed. Details: %(msg)s",
                    msg=msg,
                    provider="Paymob:"
                ))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(_("%s Could not establish the connection to the API.", "Paymob:"))
        return response.json()

    # === BUSINESS METHODS - GETTERS === #

    def _get_country_from_currency(self):
        if self.available_currency_ids.name:
            return const.PAYMOB_CONFIG[self.available_currency_ids.name]['country_code']

    def _get_paymob_account_currency(self):
        currency = [
            currency for currency, currency_config
            in const.PAYMOB_CONFIG.items()
            if currency_config['country_code'] == self.paymob_account_country_id.code
        ]
        if currency:
            return currency[0]

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'paymob':
            if self.paymob_account_country_id:
                supported_currencies = supported_currencies.filtered(
                    lambda c: c.name == self._get_paymob_account_currency()
                )[0]
            else:
                supported_currencies = supported_currencies.filtered(
                    lambda c: c.name in const.PAYMOB_CONFIG
                )[0]
        return supported_currencies

    def _paymob_get_api_url(self):
        """ Return the API URL according to the provider country.

        Note: self.ensure_one()

        :return: The API URL
        :rtype: str
        """
        self.ensure_one()
        api_prefix = const.PAYMOB_CONFIG[self.available_currency_ids.name]['api_prefix']
        url = f"https://{api_prefix}.paymob.com"
        return url

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'paymob':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _paymob_get_inline_form_values(self, currency=None):
        """ Return a serialized JSON of the required values to render the inline form.

        Note: `self.ensure_one()`

        :param res.currency currency: The transaction currency.
        :return: The JSON serial of the required values to render the inline form.
        :rtype: str
        """
        inline_form_values = {
            'provider_id': self.id,
            'client_id': self.paymob_client_id,
            'currency_code': currency and currency.name,
        }
        return json.dumps(inline_form_values)

    def _paymob_fetch_access_token(self):
        """ Generate a new access token if it's expired, otherwise return the existing access token.
        Paymob's access tokens expire every hour.

        :return: A valid access token.
        :rtype: str
        :raise ValidationError: If the access token can not be fetched.
        """
        if not self.paymob_access_token or fields.Datetime.now() > self.paymob_access_token_expiry:
            response_content = self._paymob_make_request(
                '/api/auth/tokens',
                data={'api_key': self.paymob_api_key},
                is_refresh_token_request=True,
                is_client_request=False,
            )
            access_token = response_content['token']
            if not access_token:
                raise ValidationError(
                    _("%(provider)s Could not generate a new access token.", provider="Paymob:")
                )
            self.write({
                'paymob_access_token': access_token,
                'paymob_access_token_expiry': fields.Datetime.now() + timedelta(minutes=55),
            })
        return self.paymob_access_token
