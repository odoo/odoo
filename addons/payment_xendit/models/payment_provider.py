# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

import requests
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import str2bool

from odoo.addons.payment_xendit import const


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('xendit', "Xendit")], ondelete={'xendit': 'set default'}
    )
    # Kept for backward compatibility with existing databases; no longer used or shown in the
    # provider form since the inline card flow it configured was replaced by hosted redirect
    # flows. Not removed, as dropping a field is not allowed in stable versions.
    xendit_public_key = fields.Char(string="Xendit Public Key", groups='base.group_system')
    xendit_secret_key = fields.Char(
        string="Xendit Secret Key", groups='base.group_system', required_if_provider='xendit'
    )
    xendit_webhook_token = fields.Char(
        string="Xendit Webhook Token", groups='base.group_system', required_if_provider='xendit'
    )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'xendit').support_tokenization = True

    # === BUSINESS METHODS - PAYMENT FLOW ===#

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'xendit':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'xendit':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _should_build_inline_form(self, is_validation=False):
        """ Override of `payment` to never build the inline form, as all Xendit payments are now
        made through a redirection.

        Databases installed before the migration to the redirect flow still have
        `inline_form_view_id` set on the noupdate provider record, and the view keeps its old card
        inputs until the module is updated.

        :param bool is_validation: Whether the operation is a validation.
        :return: Whether the inline form should be instantiated.
        :rtype: bool
        """
        if self.code != 'xendit':
            return super()._should_build_inline_form(is_validation=is_validation)
        return False

    def _get_validation_currency(self):
        """ Override of `payment` to prefer the company's currency for validation operations.

        Xendit's payment channels are activated per country, and picking an arbitrary supported
        currency unrelated to the merchant's own country (as the base implementation would for a
        company whose currency isn't the first found) can make Xendit reject the request.

        Note: `self.ensure_one()`

        :return: The validation currency.
        :rtype: recordset of `res.currency`
        """
        self.ensure_one()
        if self.code == 'xendit' and self.company_id.currency_id.name in const.SUPPORTED_CURRENCIES:
            return self.company_id.currency_id
        return super()._get_validation_currency()

    def _xendit_make_request(self, endpoint, payload=None):
        """ Make a POST request to Xendit API and return the JSON-formatted content of the response.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        return self._xendit_send_request(endpoint, payload=payload)

    def _xendit_send_request(self, endpoint, payload=None, api_version=None, method='POST'):
        """ Make a request to Xendit API and return the JSON-formatted content of the response.

        Unlike `_xendit_make_request`, whose signature is kept unchanged for backward
        compatibility, this also supports GET requests and versioned endpoints.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str api_version: The API version to be used for the request, if any.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        url = f'https://api.xendit.co/{endpoint}'
        auth = (self.xendit_secret_key, '')
        headers = {}
        if api_version:
            headers['api-version'] = api_version
        try:
            if method == 'GET':
                response = requests.get(url, auth=auth, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=payload, auth=auth, headers=headers, timeout=10)
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError("Xendit: " + _("Could not establish the connection to the API."))
        except requests.exceptions.HTTPError as err:
            error_message = err.response.json().get('message')
            _logger.exception(
                "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload)
            )
            raise ValidationError(
                "Xendit: " + _(
                    "The communication with the API failed. Xendit gave us the following"
                    " information: '%s'", error_message
                )
            )
        return response.json()

    # === BUSINESS METHODS - GETTERS === #

    def _get_redirect_form_view(self, is_validation=False):
        """ Override of `payment` kept for backward compatibility.

        Validation operations used to skip the redirect form, as `Card` was implemented using a
        direct flow. They now go through the redirect flow like any other operation.

        :param bool is_validation: Whether the operation is a validation.
        :return: The view of the redirect form template.
        :rtype: ir.ui.view
        """
        return super()._get_redirect_form_view(is_validation=is_validation)

    # === BUSINESS METHODS - AUTOVACUUM ===#

    @api.autovacuum
    def _autovacuum_notify_xendit_webhook_migration(self):
        """ Remind admins to update the Xendit webhook configuration for v3.

        Hooks into the daily autovacuum cron instead of a dedicated one or an upgrade-triggered
        migration script: SaaS/.sh don't force module upgrades, so a migration script would only
        catch the providers, companies, and admins that existed at the exact moment of the
        upgrade, and a dedicated `ir.cron` record wouldn't exist on already-installed databases
        until then either. `@api.autovacuum` methods are discovered directly from the Python
        class, so they run immediately everywhere.

        The reminder is only sent once per database, tracked through a system parameter so that
        admins aren't notified again after marking it as done. Providers configured afterwards
        are set up following the new webhook configuration, and don't need it.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        if str2bool(ICP.get_param('payment_xendit.v3_notification_sent', 'False')):
            return

        admin_groups = self.env['res.groups']
        for xmlid in (
            'base.group_system', 'account.group_account_manager', 'sales_team.group_sale_manager'
        ):
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                admin_groups |= group

        summary = _("Update the Xendit webhook configuration")
        dashboard_url = 'https://dashboard.xendit.co/settings/developers#webhooks'
        doc_url = (
            'https://www.odoo.com/documentation/master/applications/finance/payment_providers'
            '/xendit.html?highlight=xendit#webhook-configuration'
        )
        webhook_link = Markup('<a href="%s" target="_blank">%s</a>') % (
            doc_url, _("webhook configuration"),
        )
        dashboard_link = Markup('<a href="%s" target="_blank">%s</a>') % (
            dashboard_url, _("Xendit Dashboard"),
        )

        for provider in self.search([('code', '=', 'xendit'), ('state', '!=', 'disabled')]):
            admins = admin_groups.mapped('users').filtered(
                lambda u: provider.company_id in u.company_ids
            )
            for user in admins:
                provider.company_id.partner_id.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_warning',
                    user_id=user.id,
                    summary=summary,
                    note=_(
                        "Xendit replaced the single webhook field used by the "
                        "%(provider)s payment provider with separate v3 event groups. "
                        "Update the %(webhook_link)s on the %(dashboard_link)s before "
                        "%(deadline)s to keep receiving payment and card token status "
                        "updates.",
                        provider=provider.display_name,
                        webhook_link=webhook_link,
                        dashboard_link=dashboard_link,
                        deadline='October 1, 2026',
                    ),
                )
        ICP.set_param('payment_xendit.v3_notification_sent', 'True')
