# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from werkzeug.urls import url_encode, url_parse

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools.urls import urljoin as url_join

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_stripe import const
from odoo.addons.payment_stripe import utils as stripe_utils
from odoo.addons.payment_stripe.controllers.main import StripeController
from odoo.addons.payment_stripe.controllers.onboarding import OnboardingController


_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('stripe', "Stripe")], ondelete={'stripe': 'set default'})
    stripe_publishable_key = fields.Char(
        string="Publishable Key",
        help="The key solely used to identify the account with Stripe",
        required_if_provider='stripe',
        copy=False,
    )
    stripe_secret_key = fields.Char(
        string="Secret Key",
        required_if_provider='stripe',
        copy=False,
        groups='base.group_system',
    )
    stripe_webhook_secret = fields.Char(
        string="Webhook Signing Secret",
        help="If a webhook is enabled on your Stripe account, this signing secret must be set to "
             "authenticate the messages sent from Stripe to Odoo.",
        copy=False,
        groups='base.group_system',
    )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'stripe').update({
            'support_express_checkout': True,
            'support_manual_capture': 'full_only',
            'support_refund': 'partial',
            'support_tokenization': True,
        })

    # === CONSTRAINT METHODS === #

    @api.constrains('state', 'stripe_publishable_key', 'stripe_secret_key')
    def _check_state_of_connected_account_is_never_test(self):
        """ Check that the provider of a connected account can never been set to 'test'.

        This constraint is defined in the present module to allow the export of the translation
        string of the `ValidationError` should it be raised by modules that would fully implement
        Stripe Connect.

        Additionally, the field `state` is used as a trigger for this constraint to allow those
        modules to indirectly trigger it when writing on custom fields. Indeed, by always writing on
        `state` together with writing on those custom fields, the constraint would be triggered.

        :return: None
        :raise ValidationError: If the provider of a connected account is set in state 'test'.
        """
        for provider in self:
            if provider.state == 'test' and provider._stripe_has_connected_account():
                raise ValidationError(_(
                    "You cannot set the provider to Test Mode while it is linked with your Stripe "
                    "account."
                ))

    def _stripe_has_connected_account(self):
        """ Return whether the provider is linked to a connected Stripe account.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.
        Note: self.ensure_one()

        :return: Whether the provider is linked to a connected Stripe account
        :rtype: bool
        """
        self.ensure_one()
        return False

    @api.constrains('state')
    def _check_onboarding_of_enabled_provider_is_completed(self):
        """ Check that the provider cannot be set to 'enabled' if the onboarding is ongoing.

        This constraint is defined in the present module to allow the export of the translation
        string of the `ValidationError` should it be raised by modules that would fully implement
        Stripe Connect.

        :return: None
        :raise ValidationError: If the provider of a connected account is set in state 'enabled'
                                while the onboarding is not finished.
        """
        for provider in self:
            if provider.state == 'enabled' and provider._stripe_onboarding_is_ongoing():
                raise ValidationError(_(
                    "You cannot set the provider state to Enabled until your onboarding to Stripe "
                    "is completed."
                ))

    def _stripe_onboarding_is_ongoing(self):
        """ Return whether the provider is linked to an ongoing onboarding to Stripe Connect.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.
        Note: self.ensure_one()

        :return: Whether the provider is linked to an ongoing onboarding to Stripe Connect
        :rtype: bool
        """
        self.ensure_one()
        return False

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.code != 'stripe':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === ACTION METHODS === #

    def action_start_onboarding(self, menu_id=None):
        """ Override of `payment` to create a Stripe Connect account and redirect the user to the
        next onboarding step.

        If the provider is already enabled, close the current window. Otherwise, generate a Stripe
        Connect onboarding link and redirect the user to it. If provided, the menu id is included in
        the URL the user is redirected to when coming back on Odoo after the onboarding. If the link
        generation failed, redirect the user to the provider form.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.
        Note: `self.ensure_one()`

        :param int menu_id: The menu from which the onboarding is started, as an `ir.ui.menu` id.
        :return: The next step action
        :rtype: dict
        :raise RedirectWarning: If the company's country is not supported.
        """
        self.ensure_one()

        if self.code != 'stripe':
            return super().action_start_onboarding(menu_id=menu_id)

        if self._stripe_get_country(self.env.company.country_id.code) not in const.SUPPORTED_COUNTRIES:
            raise RedirectWarning(
                _(
                    "Stripe Connect is not available in your country, please use another payment"
                    " provider."
                ),
                self.env.ref('payment.action_payment_provider').id,
                _("Other Payment Providers"),
            )

        if self.state == 'enabled':
            action = {'type': 'ir.actions.act_window_close'}
        else:
            # Account creation
            connected_account = self._stripe_fetch_or_create_connected_account()

            # Link generation
            if not menu_id:
                # Fall back on `account_payment`'s menu if it is installed. If not, the user is
                # redirected to the provider's form view but without any menu in the breadcrumb.
                menu = self.env.ref('account_payment.payment_provider_menu', False)
                menu_id = menu and menu.id  # Only set if `account_payment` is installed.

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
                    'model': 'payment.provider',
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
            webhook = self._send_api_request(
                'POST', 'webhook_endpoints', data={
                    'url': self._get_stripe_webhook_url(),
                    'enabled_events[]': const.HANDLED_WEBHOOK_EVENTS,
                    'api_version': const.API_VERSION,
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

    def action_stripe_verify_apple_pay_domain(self):
        """ Verify the web domain with Stripe to enable Apple Pay.

        The domain is sent to Stripe API for them to verify that it is valid by making a request to
        the `/.well-known/apple-developer-merchantid-domain-association` route. If the domain is
        valid, it is registered to use with Apple Pay.
        See https://stripe.com/docs/stripe-js/elements/payment-request-button#verifying-your-domain-with-apple-pay.

        :returns: A client action with a success message.
        :rtype: dict
        :raise UserError: If test keys are used to send the request.
        """
        self.ensure_one()

        web_domain = url_parse(self.get_base_url()).netloc
        response_content = self._send_api_request('POST', 'apple_pay/domains', data={
            'domain_name': web_domain
        })
        if not response_content['livemode']:
            # If test keys are used to send the request, Stripe will respond with an HTTP 200 but
            # will not register the domain. Ask the user to use live credentials.
            raise UserError(_("Please use live credentials to enable Apple Pay."))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _("Your web domain was successfully verified."),
                'type': 'success',
            },
        }

    def _get_stripe_webhook_url(self):
        return url_join(self.get_base_url(), StripeController._webhook_url)

    # === BUSINESS METHODS - PAYMENT FLOW === #

    def _stripe_get_publishable_key(self):
        """ Return the publishable key of the provider.

        This getter allows fetching the publishable key from a QWeb template and through Stripe's
        utils.

        Note: `self.ensure_one()

        :return: The publishable key.
        :rtype: str
        """
        self.ensure_one()
        return stripe_utils.get_publishable_key(self.sudo())

    def _stripe_get_inline_form_values(
        self, amount, currency, partner_id, is_validation, payment_method_sudo=None, **kwargs
    ):
        """Return a serialized JSON of the required values to render the inline form.

        Note: `self.ensure_one()`

        :param float amount: The amount in major units, to convert in minor units.
        :param res.currency currency: The currency of the transaction.
        :param int partner_id: The partner of the transaction, as a `res.partner` id.
        :param bool is_validation: Whether the operation is a validation.
        :param payment.method payment_method_sudo: The sudoed payment method record to which the
                                                   inline form belongs.
        :return: The JSON serial of the required values to render the inline form.
        :rtype: str
        """
        self.ensure_one()

        if not is_validation:
            currency_name = currency and currency.name.lower()
        else:
            currency_name = self.with_context(
                validation_pm=payment_method_sudo  # Will be converted to a kwarg in master.
            )._get_validation_currency().name.lower()
        partner = self.env['res.partner'].with_context(show_address=1).browse(partner_id).exists()
        inline_form_values = {
            'publishable_key': self._stripe_get_publishable_key(),
            'currency_name': currency_name,
            'minor_amount': amount and payment_utils.to_minor_currency_units(
                amount,
                currency,
                arbitrary_decimal_number=const.CURRENCY_DECIMALS.get(currency.name),
            ),
            'capture_method': 'manual' if self.capture_manually else 'automatic',
            'billing_details': {
                'name': partner.name or '',
                'email': partner.email or '',
                'phone': partner.phone or '',
                'address': {
                    'line1': partner.street or '',
                    'line2': partner.street2 or '',
                    'city': partner.city or '',
                    'state': partner.state_id.code or '',
                    'country': partner.country_id.code or '',
                    'postal_code': partner.zip or '',
                },
            },
            'is_tokenization_required': (
                self.allow_tokenization
                and self._is_tokenization_required(**kwargs)
                and payment_method_sudo.support_tokenization
            ),
            'payment_methods_mapping': const.PAYMENT_METHODS_MAPPING,
        }
        return json.dumps(inline_form_values)

    def _stripe_get_country(self, country_code):
        """Return the mapped country code of the company.

        Businesses in supported outlying territories should register for a Stripe account with the
        parent territory selected as the Country.

        :param str country_code: The country code of the company.
        :return: The mapped country code.
        :rtype: str
        """
        return const.COUNTRY_MAPPING.get(country_code, country_code)

    # === BUSINESS METHODS - STRIPE CONNECT ONBOARDING === #

    def _stripe_fetch_or_create_connected_account(self):
        """ Fetch the connected Stripe account and create one if not already done.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.

        :return: The connected account
        :rtype: dict
        """
        proxy_payload = self._prepare_json_rpc_payload(
            self._stripe_prepare_connect_account_payload()
        )
        return self._send_api_request('POST', 'accounts', json=proxy_payload, is_proxy_request=True)

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
            'country': self._stripe_get_country(self.company_id.country_id.code),
            'email': self.company_id.email,
            'business_type': 'company',
            'company[address][city]': self.company_id.city or '',
            'company[address][country]': self._stripe_get_country(self.company_id.country_id.code),
            'company[address][line1]': self.company_id.street or '',
            'company[address][line2]': self.company_id.street2 or '',
            'company[address][postal_code]': self.company_id.zip or '',
            'company[address][state]': self.company_id.state_id.name or '',
            'company[name]': self.company_id.name,
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
        return_params = dict(provider_id=self.id, menu_id=menu_id)
        refresh_params = dict(**return_params, account_id=connected_account_id)

        payload = {
            'account': connected_account_id,
            'return_url': f'{url_join(base_url, return_url)}?{url_encode(return_params)}',
            'refresh_url': f'{url_join(base_url, refresh_url)}?{url_encode(refresh_params)}',
            'type': 'account_onboarding',
        }
        proxy_payload = self._prepare_json_rpc_payload(payload)

        account_link = self._send_api_request(
            'POST', 'account_links', json=proxy_payload, is_proxy_request=True
        )
        return account_link['url']

    def _prepare_json_rpc_payload(self, data):
        res = super()._prepare_json_rpc_payload(data)
        if self.code != 'stripe':
            return res
        res['params'] = {
            'payload': data,  # Stripe data.
            'proxy_data': self._stripe_prepare_proxy_data(stripe_payload=data),
        }
        return res

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

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, *, is_proxy_request=False, version=1, **kwargs):
        if self.code != 'stripe':
            return super()._build_request_url(
                endpoint, is_proxy_request=is_proxy_request, version=version, **kwargs
            )
        if is_proxy_request:
            return url_join(const.PROXY_URL, f'{version}/{endpoint}')
        return url_join('https://api.stripe.com/v1/', endpoint)

    def _build_request_headers(
        self, method, *args, idempotency_key=None, is_proxy_request=False, **kwargs
    ):
        if self.code != 'stripe':
            return super()._build_request_headers(
                method,
                *args,
                idempotency_key=idempotency_key,
                is_proxy_request=is_proxy_request,
                **kwargs,
            )

        if is_proxy_request:
            return {}

        headers = {
            'AUTHORIZATION': f'Bearer {stripe_utils.get_secret_key(self)}',
            'Stripe-Version': const.API_VERSION,  # SetupIntent requires a specific version.
            **self._get_stripe_extra_request_headers(),
        }
        if method == 'POST' and idempotency_key:
            headers['Idempotency-Key'] = idempotency_key
        return headers

    def _parse_response_error(self, response):
        if self.code != 'stripe':
            return super()._parse_response_error(response)
        return response.json().get('error', {}).get('message', '')

    def _parse_response_content(self, response, *, is_proxy_request=False, **kwargs):
        if self.code != 'stripe' or not is_proxy_request:
            return super()._parse_response_content(
                response, is_proxy_request=is_proxy_request, **kwargs
            )
        return self._parse_proxy_response(response)

    def _get_stripe_extra_request_headers(self):
        """ Return the extra headers for the Stripe API request.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.

        :return: The extra request headers.
        :rtype: dict
        """
        return {}
