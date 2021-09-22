# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_adyen.const import API_ENDPOINT_VERSIONS

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('adyen', "Adyen")], ondelete={'adyen': 'set default'})
    adyen_merchant_account = fields.Char(
        string="Merchant Account",
        help="The code of the merchant account to use with this acquirer",
        required_if_provider='adyen', groups='base.group_system')
    adyen_api_key = fields.Char(
        string="API Key", help="The API key of the webservice user", required_if_provider='adyen',
        groups='base.group_system')
    adyen_client_key = fields.Char(
        string="Client Key", help="The client key of the webservice user",
        required_if_provider='adyen')
    adyen_hmac_key = fields.Char(
        string="HMAC Key", help="The HMAC key of the webhook", required_if_provider='adyen',
        groups='base.group_system')
    adyen_checkout_api_url = fields.Char(
        string="Checkout API URL", help="The base URL for the Checkout API endpoints",
        required_if_provider='adyen')
    adyen_recurring_api_url = fields.Char(
        string="Recurring API URL", help="The base URL for the Recurring API endpoints",
        required_if_provider='adyen')

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            self._adyen_trim_api_urls(values)
        return super().create(values_list)

    def write(self, values):
        self._adyen_trim_api_urls(values)
        return super().write(values)

    @api.model
    def _adyen_trim_api_urls(self, values):
        """ Remove the version and the endpoint from the url of Adyen API fields.

        :param dict values: The create or write values
        :return: None
        """
        for field_name in ('adyen_checkout_api_url', 'adyen_recurring_api_url'):
            if values.get(field_name):  # Test the value in case we're duplicating an acquirer
                values[field_name] = re.sub(r'[vV]\d+(/.*)?', '', values[field_name])

    #=== BUSINESS METHODS ===#

    def _adyen_make_request(
        self, url_field_name, endpoint, endpoint_param=None, payload=None, method='POST'
    ):
        """ Make a request to Adyen API at the specified endpoint.

        Note: self.ensure_one()

        :param str url_field_name: The name of the field holding the base URL for the request
        :param str endpoint: The endpoint to be reached by the request
        :param str endpoint_param: A variable required by some endpoints which are interpolated with
                                   it if provided. For example, the acquirer reference of the source
                                   transaction for the '/payments/{}/refunds' endpoint.
        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :return: The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """

        def _build_url(_base_url, _version, _endpoint):
            """ Build an API URL by appending the version and endpoint to a base URL.

            The final URL follows this pattern: `<_base>/V<_version>/<_endpoint>`.

            :param str _base_url: The base of the url prefixed with `https://`
            :param int _version: The version of the endpoint
            :param str _endpoint: The endpoint of the URL.
            :return: The final URL
            :rtype: str
            """
            _base = _base_url.rstrip('/')  # Remove potential trailing slash
            _endpoint = _endpoint.lstrip('/')  # Remove potential leading slash
            return f'{_base}/V{_version}/{_endpoint}'

        self.ensure_one()

        base_url = self[url_field_name]  # Restrict request URL to the stored API URL fields
        version = API_ENDPOINT_VERSIONS[endpoint]
        endpoint = endpoint if not endpoint_param else endpoint.format(endpoint_param)
        url = _build_url(base_url, version, endpoint)
        headers = {'X-API-Key': self.adyen_api_key}
        try:
            response = requests.request(method, url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", url)
            raise ValidationError("Adyen: " + _("Could not establish the connection to the API."))
        except requests.exceptions.HTTPError as error:
            _logger.exception(
                "invalid API request at %s with data %s: %s", url, payload, error.response.text
            )
            raise ValidationError("Adyen: " + _("The communication with the API failed."))
        return response.json()

    def _adyen_compute_shopper_reference(self, partner_id):
        """ Compute a unique reference of the partner for Adyen.

        This is used for the `shopperReference` field in communications with Adyen and stored in the
        `adyen_shopper_reference` field on `payment.token` if the payment method is tokenized.

        :param recordset partner_id: The partner making the transaction, as a `res.partner` id
        :return: The unique reference for the partner
        :rtype: str
        """
        return f'ODOO_PARTNER_{partner_id}'

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'adyen':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_adyen.payment_method_adyen').id
