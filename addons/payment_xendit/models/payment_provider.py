# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.tools.urls import urljoin

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_xendit import const

_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("xendit", "Xendit")], ondelete={"xendit": "set default"}
    )
    # Kept for backward compatibility with existing databases; no longer used or shown in the
    # provider form since the inline card flow it configured was replaced by hosted redirect
    # flows. Not removed, as dropping a field is not allowed in stable versions.
    xendit_public_key = fields.Char(
        string="Xendit Public Key",
        copy=False,
        groups="base.group_system",
    )
    xendit_secret_key = fields.Char(
        string="Xendit Secret Key",
        required_if_provider="xendit",
        copy=False,
        groups="base.group_system",
    )
    xendit_webhook_token = fields.Char(
        string="Xendit Webhook Token",
        required_if_provider="xendit",
        copy=False,
        groups="base.group_system",
    )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """Override of `payment` to enable additional features."""
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == "xendit").support_tokenization = True

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "xendit":
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code != "xendit":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS === #

    def _get_validation_currency(self):
        """Override of `payment` to prefer the company's currency for validation operations.

        Xendit's payment channels are activated per country, and picking an arbitrary supported
        currency unrelated to the merchant's own country (as the base implementation would for a
        company whose currency isn't the first found) can make Xendit reject the request.

        Note: `self.ensure_one()`

        :return: The validation currency.
        :rtype: recordset of `res.currency`
        """
        self.ensure_one()
        if self.code == "xendit" and self.company_id.currency_id.name in const.SUPPORTED_CURRENCIES:
            return self.company_id.currency_id
        return super()._get_validation_currency()

    def _get_redirect_form_view(self, is_validation=False):
        """Override of `payment` kept for backward compatibility.

        Validation operations used to skip the redirect form, as `Card` was implemented using a
        direct flow. They now go through the redirect flow like any other operation.

        :param bool is_validation: Whether the operation is a validation.
        :return: The view of the redirect form template.
        :rtype: ir.ui.view
        """
        return super()._get_redirect_form_view(is_validation=is_validation)

    # === REQUEST HELPERS ===#

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != "xendit":
            return super()._build_request_url(endpoint, **kwargs)
        return urljoin("https://api.xendit.co/", endpoint)

    def _build_request_headers(self, method, endpoint, payload, *, api_version=None, **kwargs):
        """Override of `payment` to set the API version header, if any."""
        if self.code != "xendit":
            return super()._build_request_headers(
                method, endpoint, payload, api_version=api_version, **kwargs
            )
        headers = {}
        if api_version:
            headers["api-version"] = api_version
        return headers

    def _build_request_auth(self, **kwargs):
        """Override of `payment` to build the request Auth."""
        if self.code != "xendit":
            return super()._build_request_auth(**kwargs)
        return self.xendit_secret_key, ""

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != "xendit":
            return super()._parse_response_error(response)
        return response.json().get("message")

    # === BUSINESS METHODS - AUTOVACUUM ===#

    @api.autovacuum
    def _autovacuum_notify_xendit_webhook_migration(self):
        """Remind admins to update the Xendit webhook configuration for v3.

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
        ICP = self.env["ir.config_parameter"].sudo()
        if ICP.get_bool("payment_xendit.v3_notification_sent"):
            return

        admin_groups = self.env["res.groups"]
        for xmlid in (
            "base.group_system",
            "account.group_account_manager",
            "sales_team.group_sale_manager",
        ):
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                admin_groups |= group

        summary = _("Update the Xendit webhook configuration")
        dashboard_url = "https://dashboard.xendit.co/settings/developers#webhooks"
        doc_url = (
            "https://www.odoo.com/documentation/master/applications/finance/payment_providers"
            "/xendit.html?highlight=xendit#webhook-configuration"
        )
        webhook_link = Markup('<a href="%s" target="_blank">%s</a>') % (
            doc_url,
            _("webhook configuration"),
        )
        dashboard_link = Markup('<a href="%s" target="_blank">%s</a>') % (
            dashboard_url,
            _("Xendit Dashboard"),
        )

        for provider in self.search([("code", "=", "xendit"), ("state", "!=", "disabled")]):
            admins = admin_groups.mapped("all_user_ids").filtered(
                lambda u: provider.company_id in u.company_ids
            )
            for user in admins:
                provider.company_id.partner_id.activity_schedule(
                    act_type_xmlid="mail.mail_activity_data_warning",
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
                        deadline="October 1, 2026",
                    ),
                )
        ICP.set_bool("payment_xendit.v3_notification_sent", True)
