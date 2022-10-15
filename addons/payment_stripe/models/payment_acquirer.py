# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import uuid

import requests
from werkzeug.urls import url_encode, url_join

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_stripe import utils as stripe_utils
from odoo.addons.payment_stripe.const import API_VERSION, PROXY_URL, WEBHOOK_HANDLED_EVENTS
from odoo.addons.payment_stripe.controllers.main import StripeController
from odoo.addons.payment_stripe.controllers.onboarding import OnboardingController


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

    #=== CONSTRAINT METHODS ===#

    @api.constrains('state', 'stripe_publishable_key', 'stripe_secret_key')
    def _check_state_of_connected_account_is_never_test(self):
        """ Check that the acquirer of a connected account can never been set to 'test'.

        This constraint is defined in the present module to allow the export of the translation
        string of the `ValidationError` should it be raised by modules that would fully implement
        Stripe Connect.

        Additionally, the field `state` is used as a trigger for this constraint to allow those
        modules to indirectly trigger it when writing on custom fields. Indeed, by always writing on
        `state` together with writing on those custom fields, the constraint would be triggered.

        :return: None
        """
        for acquirer in self:
            if acquirer.state == 'test' and acquirer._stripe_has_connected_account():
                raise ValidationError(_(
                    "You cannot set the acquirer to Test Mode while it is linked with your Stripe "
                    "account."
                ))

    def _stripe_has_connected_account(self):
        """ Return whether the acquirer is linked to a connected Stripe account.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.
        Note: self.ensure_one()

        :return: Whether the acquirer is linked to a connected Stripe account
        :rtype: bool
        """
        self.ensure_one()
        return False

    # === ACTION METHODS === #

    def action_stripe_connect_account(self, menu_id=None):
        """ Create a Stripe Connect account and redirect the user to the next onboarding step.

        If the acquirer is already enabled, close the current window. Otherwise, generate a Stripe
        Connect onboarding link and redirect the user to it. If provided, the menu id is included in
        the URL the user is redirected to when coming back on Odoo after the onboarding. If the link
        generation failed, redirect the user to the acquirer form.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.
        Note: self.ensure_one()

        :param int menu_id: The menu from which the user started the onboarding step, as an
                            `ir.ui.menu` id.
        :return: The next step action
        :rtype: dict
        """
        self.ensure_one()

        if self.state == 'enabled':
            self.company_id._mark_payment_onboarding_step_as_done()
            action = {'type': 'ir.actions.act_window_close'}
        else:
            # Account creation
            connected_account = self._stripe_fetch_or_create_connected_account()

            # Link generation
            menu_id = menu_id or self.env.ref('payment.payment_acquirer_menu').id
            account_link_url = self._stripe_create_account_link(connected_account['id'], menu_id)
            if account_link_url:
                action = {
                    'type': 'ir.actions.act_url',
                    'url': account_link_url,
                    'target': 'self',
                }
            else:
                action = {
                    'type': 'ir.actions.act_window',
                    'model': 'payment.acquirer',
                    'views': [[False, 'form']],
                    'res_id': self.id,
                }

        return action

    def action_stripe_create_webhook(self):
        """ Create a webhook and return a feedback notification.

        Note: This action only works for instances using a public URL

        :return: The feedback notification
        :rtype: dict
        """
        self.ensure_one()

        if self.stripe_webhook_secret:
            message = _("Your Stripe Webhook is already set up.")
            notification_type = 'warning'
        elif not self.stripe_secret_key:
            message = _("You cannot create a Stripe Webhook if your Stripe Secret Key is not set.")
            notification_type = 'danger'
        else:
            webhook = self._stripe_make_request(
                'webhook_endpoints', payload={
                    'url': self._get_stripe_webhook_url(),
                    'enabled_events[]': WEBHOOK_HANDLED_EVENTS,
                    'api_version': API_VERSION,
                }
            )
            self.stripe_webhook_secret = webhook.get('secret')
            message = _("You Stripe Webhook was successfully set up!")
            notification_type = 'info'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'sticky': False,
                'type': notification_type,
                'next': {'type': 'ir.actions.act_window_close'},  # Refresh the form to show the key
            }
        }

    def _get_stripe_webhook_url(self):
        return url_join(self.get_base_url(), StripeController._webhook_url)

    # === BUSINESS METHODS - PAYMENT FLOW === #

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

        url = url_join('https://api.stripe.com/v1/', endpoint)
        headers = {
            'AUTHORIZATION': f'Bearer {stripe_utils.get_secret_key(self)}',
            'Stripe-Version': API_VERSION,  # SetupIntent requires a specific version.
            **self._get_stripe_extra_request_headers(),
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

    def _get_stripe_extra_request_headers(self):
        """ Return the extra headers for the Stripe API request.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.

        :return: The extra request headers.
        :rtype: dict
        """
        return {}

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'stripe':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_stripe.payment_method_stripe').id

    # === BUSINESS METHODS - STRIPE CONNECT ONBOARDING === #

    def _stripe_fetch_or_create_connected_account(self):
        """ Fetch the connected Stripe account and create one if not already done.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.

        :return: The connected account
        :rtype: dict
        """
        return self._stripe_make_proxy_request(
            'accounts', payload=self._stripe_prepare_connect_account_payload()
        )

    def _stripe_prepare_connect_account_payload(self):
        """ Prepare the payload for the creation of a connected account in Stripe format.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.
        Note: self.ensure_one()

        :return: The Stripe-formatted payload for the creation request
        :rtype: dict
        """
        self.ensure_one()

        return {
            'type': 'standard',
            'country': self.company_id.country_id.code,
            'email': self.company_id.email,
            'business_type': 'individual',
            'company[address][city]': self.company_id.city or '',
            'company[address][country]': self.company_id.country_id.code or '',
            'company[address][line1]': self.company_id.street or '',
            'company[address][line2]': self.company_id.street2 or '',
            'company[address][postal_code]': self.company_id.zip or '',
            'company[address][state]': self.company_id.state_id.name or '',
            'company[name]': self.company_id.name,
            'individual[address][city]': self.company_id.city or '',
            'individual[address][country]': self.company_id.country_id.code or '',
            'individual[address][line1]': self.company_id.street or '',
            'individual[address][line2]': self.company_id.street2 or '',
            'individual[address][postal_code]': self.company_id.zip or '',
            'individual[address][state]': self.company_id.state_id.name or '',
            'individual[email]': self.company_id.email or '',
            'business_profile[name]': self.company_id.name,
        }

    def _stripe_create_account_link(self, connected_account_id, menu_id):
        """ Create an account link and return its URL.

        An account link url is the beginning URL of Stripe Onboarding.
        This URL is only valid once, and can only be used once.

        Note: self.ensure_one()

        :param str connected_account_id: The id of the connected account.
        :param int menu_id: The menu from which the user started the onboarding step, as an
                            `ir.ui.menu` id
        :return: The account link URL
        :rtype: str
        """
        self.ensure_one()

        base_url = self.company_id.get_base_url()
        return_url = OnboardingController._onboarding_return_url
        refresh_url = OnboardingController._onboarding_refresh_url
        return_params = dict(acquirer_id=self.id, menu_id=menu_id)
        refresh_params = dict(**return_params, account_id=connected_account_id)

        account_link = self._stripe_make_proxy_request('account_links', payload={
            'account': connected_account_id,
            'return_url': f'{url_join(base_url, return_url)}?{url_encode(return_params)}',
            'refresh_url': f'{url_join(base_url, refresh_url)}?{url_encode(refresh_params)}',
            'type': 'account_onboarding',
        })
        return account_link['url']

    def _stripe_make_proxy_request(self, endpoint, payload=None, version=1):
        """ Make a request to the Stripe proxy at the specified endpoint.

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
            'params': {
                'payload': payload,  # Stripe data.
                'proxy_data': self._stripe_prepare_proxy_data(stripe_payload=payload),
            },
        }
        url = url_join(PROXY_URL, f'{version}/{endpoint}')
        try:
            response = requests.post(url=url, json=proxy_payload, timeout=60)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", url)
            raise ValidationError(_("Stripe Proxy: Could not establish the connection."))
        except requests.exceptions.HTTPError:
            _logger.exception("invalid API request at %s with data %s", url, payload)
            raise ValidationError(
                _("Stripe Proxy: An error occurred when communicating with the proxy.")
            )

        # Stripe proxy endpoints always respond with HTTP 200 as they implement JSON-RPC 2.0
        response_content = response.json()
        if response_content.get('error'):  # An exception was raised on the proxy
            error_data = response_content['error']['data']
            _logger.error("request forwarded with error: %s", error_data['message'])
            raise ValidationError(_("Stripe Proxy error: %(error)s", error=error_data['message']))

        return response_content.get('result', {})

    def _stripe_prepare_proxy_data(self, stripe_payload=None):
        """ Prepare the contextual data passed to the proxy when making a request.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.
        Note: self.ensure_one()

        :param dict stripe_payload: The part of the request payload to be forwarded to Stripe.
        :return: The proxy data.
        :rtype: dict
        """
        self.ensure_one()

        return {}
