# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint
from datetime import datetime, timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command

from odoo.addons.payment_paymob import const


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('paymob', "Paymob")], ondelete={'paymob': 'set default'}
    )
    paymob_account_country_id = fields.Many2one(
        string="Paymob Account Country",
        help="The country of the Paymob account. The currency will be updated to match the country"
             " of the Paymob account.",
        comodel_name='res.country',
        inverse='_inverse_paymob_account_country_id',
        domain=f'[("code", "in", {list(const.API_MAPPING.keys())})]',
        required_if_provider='paymob',
    )
    paymob_public_key = fields.Char(string="Paymob Public Key", required_if_provider='paymob')
    paymob_secret_key = fields.Char(
        string="Paymob Secret Key", required_if_provider='paymob', groups='base.group_system'
    )
    paymob_hmac_key = fields.Char(string="Paymob HMAC Key", required_if_provider='paymob')
    paymob_api_key = fields.Char(string="Paymob API Key", required_if_provider='paymob')
    paymob_access_token = fields.Char(groups='base.group_system')
    paymob_access_token_expiry = fields.Datetime(default='1970-01-01', groups='base.group_system')

    # ==== CONSTRAINT METHODS === #

    @api.constrains('available_currency_ids')
    def _check_available_country_currency_ids(self):
        for provider in self.filtered(lambda p: p.code == 'paymob'):
            if len(provider.available_currency_ids) > 1:
                raise ValidationError(_("Only one currency can be selected per Paymob account."))
            if (
                provider.available_currency_ids
                and provider.available_currency_ids.name not in const.CURRENCY_MAPPING.values()
            ):
                raise ValidationError(_("Only currencies supported by Paymob can be selected."))

    # === COMPUTE METHODS === #

    def _inverse_paymob_account_country_id(self):
        for provider in self.filtered(lambda p: p.code == 'paymob'):
            if self.paymob_account_country_id.code:
                currency_code = const.CURRENCY_MAPPING.get(self.paymob_account_country_id.code)
                currency = self.env['res.currency'].with_context(
                    active_test=False,
                ).search([('name', '=', currency_code)], limit=1)
                provider.available_currency_ids = [Command.set(currency.ids)]

    # === ACTION METHODS === #

    def action_sync_paymob_payment_methods(self):
        """ Synchronize the payment methods with the ones on the Paymob portal, the integration_name
        needs to be set to be able to communicate with the `payment_method.code` when the intention
        is created.

        :return: A notification with the status of the action.
        :rtype: dict
        """
        params = {
            'is_plugin': 'true',
            'page_size': 500,
            'is_deprecated': 'false',
            'is_standalone': 'false',
            'is_live': self.state == 'enabled',
        }
        paymob_gateways_data = self._paymob_make_request(
            '/api/ecommerce/integrations', payload=params, method='GET'
        )['results']
        matched_gateways_data = self._match_paymob_payment_methods(paymob_gateways_data)

        displayed_notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {},
        }
        if len(matched_gateways_data) < len(self.payment_method_ids):
            displayed_notification['params'].update({
                'type': 'warning',
                'title': _("Payment methods not found"),
                'message': _("Not all enabled payment methods were found on your account."),
            })
            return displayed_notification

        # Update the name and return urls of payment methods on the Paymob portal.
        self._update_payment_method_integration_names(matched_gateways_data)

        # All payment methods were successfully updated.
        displayed_notification['params'].update({
            'type': 'success',
            'title': _("Successfully synchronized with Paymob"),
            'message': _("Payment methods have been successfully set up!"),
        })
        return displayed_notification

    def _match_paymob_payment_methods(self, paymob_gateways_data):
        """ Filter gateways available in Paymob to match the payment methods enabled in Odoo.

        This method takes the full list of gateways from Paymob, and while avoiding duplicates,
        returns only those that:

        1. Have a gateway_type mapped to an Odoo payment method code.
        2. Are available for the current provider.
        3. Are not Apple Pay or Google Pay (currently unsupported for mobile-only payments).
        4. Are not a saved card (currently unsupported).
        5. Are not an Authorize/Capture payment methods (currently unsupported).

        :param list[dict] paymob_gateways_data: The gateways data returned by the Paymob API.
        :return: All the matched Paymob gateways' data.
        :rtype: list
        """
        available_payment_method_codes = self.payment_method_ids.mapped('code')
        sorted_gateways_data = sorted(
            paymob_gateways_data,
            key=lambda x: datetime.strptime((x['created_at']), "%Y-%m-%dT%H:%M:%S.%f"),
            reverse=True,
        )
        matched_gateways_data = []
        for gateway_data in sorted_gateways_data:
            if not available_payment_method_codes:  # All available payment methods are now matched.
                break
            integration_name = gateway_data.get('integration_name') or ''
            is_apple_pay = 'apple' in integration_name.lower()
            is_google_pay = 'google' in integration_name.lower()
            if is_apple_pay or is_google_pay:
                # Apple Pay and Google Pay are not supported at the moment.
                continue
            gateway_type = gateway_data.get('gateway_type')
            payment_method_code = const.PAYMENT_METHODS_MAPPING.get(gateway_type)
            if payment_method_code == 'card' and (
                # Tokenization and manual capture are not supported at the moment.
                gateway_data['integration_type'] == 'moto' or gateway_data['is_auth']
            ):
                continue
            if payment_method_code in available_payment_method_codes:
                matched_gateways_data.append(gateway_data)
                # In some cases, paymob accounts might have multiple gateway data for the same
                # payment method, only the most recent gateway_data should be considered
                available_payment_method_codes.remove(payment_method_code)
        return matched_gateways_data

    def _update_payment_method_integration_names(self, matched_gateways_data):
        """ Set the integration name given to the gateways on Paymob to the corresponding payment
        method code.

        The integration names acts as the identifier to specify which payment method is to be used
        for every transaction.

        :param list matched_gateways_data: The gateways data matching payment methods in Odoo.
        :return: None
        """
        for gateway_data in matched_gateways_data:
            payment_method_code = const.PAYMENT_METHODS_MAPPING[gateway_data['gateway_type']]
            if payment_method_code == 'card' and gateway_data.get('installments'):
                installment_payment_method = self.env['payment.method'].search(
                    [('code', '=', 'installments_eg')], limit=1
                )
                if not installment_payment_method:
                    continue
                payment_method_code = 'installments_eg'
            environment = 'live' if self.state == 'enabled' else 'test'
            payload = {'integration_name': f'{payment_method_code.replace("_", "")}{environment}'}
            self._paymob_make_request(
                f'/api/ecommerce/integrations/{gateway_data["id"]}', method='PUT', payload=payload
            )

    # === BUSINESS METHODS === #

    def _paymob_make_request(
        self, endpoint, payload=None, method='POST', is_refresh_token_request=False,
        is_client_request=False,
    ):
        """ Make a request to Paymob API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The method of the request.
        :param bool is_refresh_token_request: Whether the request is for refreshing the access
                                              token.
        :param bool is_client_request: Whether the request is a client request or a backend request.
                                       It will depend what auth will be sent the access token
                                       generated from the api_key or the secret_key.
        :return: The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        url = f'{self._paymob_get_api_url()}{endpoint}'
        auth = ''
        if not is_refresh_token_request and is_client_request:
            auth = self.paymob_secret_key
        elif not is_refresh_token_request:
            auth = self._paymob_fetch_access_token()
        headers = {'Authorization': f'Bearer {auth}'}
        try:
            if method in ['POST', 'PUT']:
                response = requests.request(method, url, headers=headers, json=payload, timeout=10)
            else:
                response = requests.get(url, headers=headers, params=payload, timeout=10)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                # Paymob errors: https://developers.paymob.com/egypt/error-codes
                _logger.exception(
                    "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload)
                )
                msg = response.text
                error_msg = _("The communication with the API failed. Details: %(msg)s", msg=msg)
                if "This field may not be blank" in msg:
                    missing_fields = ", ".join(json.loads(msg).get('billing_data', {}).keys())
                    error_msg = _(
                        "The following fields must be filled: %(fields)s", fields=missing_fields
                    )
                raise ValidationError(error_msg)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(_("Could not establish the connection to the API."))
        return response.json()

    # === BUSINESS METHODS - GETTERS === #

    def _paymob_get_api_url(self):
        """ Get the API URL according to the provider country.

        Note: self.ensure_one()

        :return: The API URL.
        :rtype: str
        """
        self.ensure_one()
        api_prefix = const.API_MAPPING[self.paymob_account_country_id.code]
        url = f'https://{api_prefix}.paymob.com'
        return url

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
                payload={'api_key': self.paymob_api_key},
                is_refresh_token_request=True,
            )
            access_token = response_content['token']
            if not access_token:
                raise ValidationError(_("Could not generate a new access token."))
            self.write({
                'paymob_access_token': access_token,
                'paymob_access_token_expiry': fields.Datetime.now() + timedelta(minutes=55),
            })
        return self.paymob_access_token

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'paymob':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
