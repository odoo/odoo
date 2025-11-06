# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import pprint

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools import urls

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_authorize import const
from odoo.addons.payment_authorize.models.authorize_request import AuthorizeAPI


_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('authorize', 'Authorize.Net')], ondelete={'authorize': 'set default'})
    authorize_login = fields.Char(
        string="API Login ID",
        help="The ID solely used to identify the account with Authorize.Net",
        required_if_provider='authorize',
        copy=False,
    )
    authorize_transaction_key = fields.Char(
        string="API Transaction Key",
        required_if_provider='authorize',
        copy=False,
        groups='base.group_system',
    )
    authorize_signature_key = fields.Char(
        string="API Signature Key",
        required_if_provider='authorize',
        copy=False,
        groups='base.group_system',
    )
    authorize_client_key = fields.Char(
        string="API Client Key",
        help="The public client key. To generate directly from Odoo or from Authorize.Net backend.",
        copy=False,
    )
    authorize_webhook_id = fields.Char(
        string="Webhook ID",
        help="The ID of the webhook created in Authorize.Net.",
        copy=False,
        groups='base.group_system',
    )

    # === CONSTRAINT METHODS ===#

    # Authorize.Net supports only one currency: "One gateway account is required for each currency"
    # See https://community.developer.authorize.net/t5/The-Authorize-Net-Developer-Blog/Authorize-Net-UK-Europe-Update/ba-p/35957
    @api.constrains('available_currency_ids', 'state')
    def _limit_available_currency_ids(self):
        for provider in self.filtered(lambda p: p.code == 'authorize'):
            if len(provider.available_currency_ids) > 1 and provider.state != 'disabled':
                raise ValidationError(
                    _("Only one currency can be selected by Authorize.Net account.")
                )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'authorize').update({
            'support_manual_capture': 'full_only',
            'support_refund': 'full_only',
            'support_tokenization': True,
        })

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.code != 'authorize':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === ACTION METHODS ===#

    def action_update_merchant_details(self):
        """ Fetch the merchant details to update the client key and the account currency. """
        self.ensure_one()

        if self.state == 'disabled':
            raise UserError(_("This action cannot be performed while the provider is disabled."))

        authorize_API = AuthorizeAPI(self)

        # Validate the API Login ID and Transaction Key
        res_content = authorize_API.test_authenticate()
        _logger.info("test_authenticate request response:\n%s", pprint.pformat(res_content))
        if res_content.get('err_msg'):
            raise UserError(_("Failed to authenticate.\n%s", res_content['err_msg']))

        # Update the merchant details
        res_content = authorize_API.merchant_details()
        _logger.info("merchant_details request response:\n%s", pprint.pformat(res_content))
        if res_content.get('err_msg'):
            raise UserError(_("Could not fetch merchant details:\n%s", res_content['err_msg']))

        currency = self.env['res.currency'].search([('name', 'in', res_content.get('currencies'))])
        self.available_currency_ids = [Command.set(currency.ids)]
        self.authorize_client_key = res_content.get('publicClientKey')

    def action_authorize_create_webhook(self):
        """Create a webhook in Authorize.Net for transaction notifications.

        Note: `self.ensure_one()`

        :return: A notification action to display the result.
        :rtype: dict
        """
        self.ensure_one()

        webhook_url = urls.urljoin(
            self.get_base_url(), '/payment/authorize/webhook'
        )
        response = self._send_api_request('POST', '/rest/v1/webhooks', json={
            'name': self.company_id.name,
            'url': webhook_url,
            'eventTypes': const.HANDLED_WEBHOOK_EVENTS,
            'status': 'active',
        })
        self.authorize_webhook_id = response.get('webhookId')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': self.env._("Your Authorize.Net webhook was successfully set up!"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    # === BUSINESS METHODS ===#

    def _get_validation_amount(self):
        """ Override of payment to return the amount for Authorize.Net validation operations.

        :return: The validation amount
        :rtype: float
        """
        res = super()._get_validation_amount()
        if self.code != 'authorize':
            return res

        return 0.01

    def _authorize_get_inline_form_values(self):
        """ Return a serialized JSON of the required values to render the inline form.

        Note: `self.ensure_one()`

        :return: The JSON serial of the required values to render the inline form.
        :rtype: str
        """
        self.ensure_one()

        inline_form_values = {
            'state': self.state,
            'login_id': self.authorize_login,
            'client_key': self.authorize_client_key,
        }
        return json.dumps(inline_form_values)

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the full URL for Authorize.Net REST API."""
        if self.code != 'authorize':
            return super()._build_request_url(endpoint, **kwargs)

        if self.state == 'enabled':
            return f'https://api.authorize.net{endpoint}'
        return f'https://apitest.authorize.net{endpoint}'

    def _build_request_auth(self, **kwargs):
        """Override of `payment` to build HTTP Basic Auth for Authorize.Net REST API."""
        if self.code != 'authorize':
            return super()._build_request_auth(**kwargs)

        return self.authorize_login, self.authorize_transaction_key
