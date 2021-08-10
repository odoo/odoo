# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import requests
from werkzeug import urls

from odoo import _, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('stripe', "Stripe")], ondelete={'stripe': 'set default'})
    stripe_publishable_key = fields.Char(
        string="Publishable Key", help="The key solely used to identify the account with Stripe",
        required_if_provider='stripe')
    stripe_secret_key = fields.Char(
        string="Secret Key", required_if_provider='stripe', groups='base.group_system')
    stripe_webhook_secret = fields.Char(
        string="Webhook Signing Secret",
        help="If a webhook is enabled on your Stripe account, this signing secret must be set to "
             "authenticate the messages sent from Stripe to Odoo.",
        groups='base.group_system')

    def _stripe_make_request(self, endpoint, payload=None, method='POST', offline=False):
        """ Make a request to Stripe API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request
        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :param bool offline: Whether the operation of the transaction being processed is 'offline'
        :return The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """
        self.ensure_one()

        url = urls.url_join('https://api.stripe.com/v1/', endpoint)
        headers = {
            'AUTHORIZATION': f'Bearer {self.stripe_secret_key}',
            'Stripe-Version': '2019-05-16',  # SetupIntent needs a specific version
        }
        try:
            response = requests.request(method, url, data=payload, headers=headers, timeout=60)
            # Stripe can send 4XX errors for payment failures (not only for badly-formed requests).
            # Check if an error code is present in the response content and raise only if not.
            # See https://stripe.com/docs/error-codes.
            # If the request originates from an offline operation, don't raise and return the resp.
            if not response.ok \
                    and not offline \
                    and 400 <= response.status_code < 500 \
                    and response.json().get('error'):  # The 'code' entry is sometimes missing
                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError:
                    _logger.exception("invalid API request at %s with data %s", url, payload)
                    error_msg = response.json().get('error', {}).get('message', '')
                    raise ValidationError(
                        "Stripe: " + _(
                            "The communication with the API failed.\n"
                            "Stripe gave us the following info about the problem:\n'%s'", error_msg
                        )
                    )
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", url)
            raise ValidationError("Stripe: " + _("Could not establish the connection to the API."))
        return response.json()

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'stripe':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_stripe.payment_method_stripe').id
