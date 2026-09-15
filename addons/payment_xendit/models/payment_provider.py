# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

import requests
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_xendit import const


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('xendit', "Xendit")], ondelete={'xendit': 'set default'}
    )
    xendit_public_key = fields.Char(
        string="Xendit Public Key", groups='base.group_system', required_if_provider='xendit'
    )
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

    def _xendit_make_request(self, endpoint, payload=None):
        """ Make a request to Xendit API and return the JSON-formatted content of the response.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        url = f'https://api.xendit.co/{endpoint}'
        auth = (self.xendit_secret_key, '')
        try:
            response = requests.post(url, json=payload, auth=auth, timeout=10)
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
        """ Override of `payment` to avoid rendering the form view for validation operations.

        Unlike other compatible payment methods in Xendit, `Card` is implemented using a direct
        flow. To avoid rendering a useless template, and also to avoid computing wrong values, this
        method returns `None` for Xendit's validation operations (Card is and will always be the
        sole tokenizable payment method for Xendit).

        Note: `self.ensure_one()`

        :param bool is_validation: Whether the operation is a validation.
        :return: The view of the redirect form template or None.
        :rtype: ir.ui.view | None
        """
        self.ensure_one()

        if self.code == 'xendit' and is_validation:
            return None
        return super()._get_redirect_form_view(is_validation)

    # === BUSINESS METHODS - AUTOVACUUM ===#

    @api.autovacuum
    def _autovacuum_notify_xendit_webhook_migration(self):
        """ Remind admins to update the Xendit webhook configuration for v3. """
        admin_groups = self.env['res.groups']
        for xmlid in ('base.group_system', 'account.group_account_manager', 'sales_team.group_sale_manager'):
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                admin_groups |= group

        warning_type = self.env.ref('mail.mail_activity_data_warning')
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
            admins = admin_groups.mapped('users').filtered(lambda u: provider.company_id in u.company_ids)
            already_notified = self.env['mail.activity'].search([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', provider.company_id.partner_id.id),
                ('activity_type_id', '=', warning_type.id),
                ('summary', '=', summary),
            ]).user_id
            for user in admins - already_notified:
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
