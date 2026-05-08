# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pprint import pformat

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import CURRENCY_MINOR_UNITS, REPORT_REASONS_MAPPING, SENSITIVE_KEYS
from odoo.addons.payment.logging import get_payment_logger

# Pass the possibly empty set of sensitive keys to the logger in case a provider module extends it.
_logger = get_payment_logger(__name__, sensitive_keys=SENSITIVE_KEYS)


class PaymentProvider(models.Model):
    _name = "payment.provider"
    _description = "Payment Provider"
    _order = "module_state, is_published desc, sequence, name"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    def _valid_field_parameter(self, field, name):
        return name == "required_if_provider" or super()._valid_field_parameter(field, name)

    # === GENERAL FIELDS === #

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Selection(
        string="Code",
        help="The technical code of this payment provider.",
        selection=[("none", "No Provider Set")],
        default="none",
        required=True,
    )
    is_live = fields.Boolean(
        string="Live",
        help="If live mode is disabled, a fake payment is processed through a test payment"
        " interface. This mode is advised when setting up the provider.",
        copy=False,
    )
    is_published = fields.Boolean(
        string="Published",
        help="Whether the provider is visible on the website or not. Tokens remain functional but"
        " are only visible on manage forms.",
        copy=False,
    )
    active = fields.Boolean(string="Active", default=True)
    sequence = fields.Integer(string="Sequence", help="Define the display order", default=1000)
    image_128 = fields.Image(string="Logo", max_width=128, max_height=128)

    # === RELATED RECORD FIELDS === #

    payment_method_ids = fields.One2many(
        string="Supported Payment Methods",
        comodel_name="payment.method",
        inverse_name="provider_id",
        context={"active_test": False},
    )
    primary_payment_method_ids = fields.One2many(
        string="Primary Payment Methods",
        comodel_name="payment.method",
        compute="_compute_primary_payment_method_ids",
        context={"active_test": False},
    )  # PMs with code "unknown" are excluded from this set
    payment_transaction_ids = fields.One2many(
        string="Payment Transactions",
        comodel_name="payment.transaction",
        inverse_name="provider_id",
    )
    processed_amount = fields.Monetary(
        string="Processed Amount",
        compute="_compute_processed_amount",
        currency_field="main_currency_id",
    )
    transaction_count = fields.Integer(
        string="Transaction Count", compute="_compute_transaction_count"
    )
    payment_token_ids = fields.One2many(
        string="Payment Tokens", comodel_name="payment.token", inverse_name="provider_id"
    )
    token_count = fields.Integer(string="Token Count", compute="_compute_token_count")

    # === FEATURE SUPPORT FIELDS === #

    support_tokenization = fields.Boolean(
        string="Tokenization", compute="_compute_feature_support_fields"
    )
    support_express_checkout = fields.Boolean(
        string="Express Checkout", compute="_compute_feature_support_fields"
    )
    support_manual_capture = fields.Selection(
        string="Manual Capture Supported",
        selection=[("full_only", "Full Only"), ("partial", "Partial")],
        compute="_compute_feature_support_fields",
    )
    support_refund = fields.Selection(
        string="Refund",
        help="Refund is a feature allowing to refund customers directly from the payment in Odoo.",
        selection=[
            ("none", "Unsupported"),
            ("full_only", "Full Only"),
            ("partial", "Full & Partial"),
        ],
        compute="_compute_feature_support_fields",
    )

    # === CONFIGURATION FIELDS === #

    allow_tokenization = fields.Boolean(
        string="Allow Saving Payment Methods",
        help="This controls whether customers can save their payment methods as payment tokens."
        " A payment token is an anonymous link to the payment method details saved in the"
        " provider's database, allowing the customer to reuse it for a next purchase.",
    )
    allow_express_checkout = fields.Boolean(
        string="Allow Express Checkout",
        help="This controls whether customers can use express payment methods. Express checkout"
        " enables customers to pay with Google Pay and Apple Pay from which address information is"
        " collected at payment.",
    )
    capture_manually = fields.Boolean(
        string="Capture Amount Manually",
        help="Capture the amount from Odoo, when the delivery is completed. Use this if you want to"
        " charge your customers cards only when you are sure you can ship the goods to them.",
    )
    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        default=lambda self: self.env.company.id,
        required=True,
        index=True,  # Indexed to speed-up ORM searches (from ir_rule or others).
    )
    main_currency_id = fields.Many2one(
        related="company_id.currency_id",
        help="The main currency of the company, used to display monetary fields.",
    )

    # === RESTRICTION FIELDS === #

    minimum_amount = fields.Monetary(
        string="Minimum Amount",
        help="The minimum payment amount that this payment provider is available for. Leave blank "
        "to make it available for any payment amount.",
        currency_field="main_currency_id",
    )
    maximum_amount = fields.Monetary(
        string="Maximum Amount",
        help="The maximum payment amount that this payment provider is available for. Leave blank"
        " to make it available for any payment amount.",
        currency_field="main_currency_id",
    )
    available_currency_ids = fields.Many2many(
        string="Currencies",
        help="The currencies available with this payment provider. Leave empty not to restrict"
        " any.",
        comodel_name="res.currency",
        relation="payment_currency_rel",
        column1="payment_provider_id",
        column2="currency_id",
        compute="_compute_available_currency_ids",
        store=True,
        readonly=False,
        context={"active_test": False},
    )
    available_country_ids = fields.Many2many(
        string="Countries",
        help="The countries in which this payment provider is available. Leave blank to make it"
        " available in all countries.",
        comodel_name="res.country",
        relation="payment_country_rel",
        column1="payment_id",
        column2="country_id",
    )

    # === MESSAGE FIELDS === #

    pre_msg = fields.Html(
        string="Help Message",
        help="The message displayed to explain and help the payment process",
        translate=True,
    )
    pending_msg = fields.Html(
        string="Pending Message",
        help="The message displayed if the order pending after the payment process",
        default=lambda _self: _self.env._(
            "Your payment has been processed but is waiting for approval."
        ),
        translate=True,
    )
    auth_msg = fields.Html(
        string="Authorize Message",
        help="The message displayed if payment is authorized",
        default=lambda _self: _self.env._("Your payment has been authorized."),
        translate=True,
    )
    done_msg = fields.Html(
        string="Done Message",
        help="The message displayed if the order is successfully done after the payment process",
        default=lambda _self: _self.env._("Your payment has been processed."),
        translate=True,
    )
    cancel_msg = fields.Html(
        string="Cancelled Message",
        help="The message displayed if the order is cancelled during the payment process",
        default=lambda _self: _self.env._("Your payment has been cancelled."),
        translate=True,
    )

    # === TEMPLATE FIELDS === #

    redirect_form_view_id = fields.Many2one(
        string="Redirect Form Template",
        help="The template rendering a form submitted to redirect the user when making a payment",
        comodel_name="ir.ui.view",
        domain=[("type", "=", "qweb")],
        ondelete="restrict",
    )
    inline_form_view_id = fields.Many2one(
        string="Inline Form Template",
        help="The template rendering the inline payment form when making a direct payment",
        comodel_name="ir.ui.view",
        domain=[("type", "=", "qweb")],
        ondelete="restrict",
    )
    token_inline_form_view_id = fields.Many2one(
        string="Token Inline Form Template",
        help="The template rendering the inline payment form when making a payment by token.",
        comodel_name="ir.ui.view",
        domain=[("type", "=", "qweb")],
        ondelete="restrict",
    )
    express_checkout_form_view_id = fields.Many2one(
        string="Express Checkout Form Template",
        help="The template rendering the express payment methods' form.",
        comodel_name="ir.ui.view",
        domain=[("type", "=", "qweb")],
        ondelete="restrict",
    )

    # === MODULE FIELDS === #

    module_id = fields.Many2one(string="Corresponding Module", comodel_name="ir.module.module")
    module_state = fields.Selection(string="Installation State", related="module_id.state")
    module_to_buy = fields.Boolean(string="Odoo Enterprise Module", related="module_id.to_buy")

    # === COMPUTE METHODS === #

    @api.depends("payment_method_ids.primary_payment_method_id", "payment_method_ids.code")
    def _compute_primary_payment_method_ids(self):
        pm_data = (
            self
            .env["payment.method"]
            .with_context(active_test=False)
            ._read_group(
                domain=[
                    ("provider_id", "in", self.ids),
                    ("primary_payment_method_id", "=", False),
                    ("code", "!=", "unknown"),
                ],
                groupby=["provider_id"],
                aggregates=["id:recordset"],
            )
        )
        pm_by_provider = {provider.id: pms for provider, pms in pm_data}
        for provider in self:
            provider.primary_payment_method_ids = pm_by_provider.get(
                provider.id, self.env["payment.method"]
            )

    @api.depends("payment_transaction_ids")
    def _compute_processed_amount(self):
        # Compute the sum of confirmed transactions, grouped by provider and currency
        transaction_data = self.env["payment.transaction"]._read_group(
            domain=[
                ("provider_id", "in", self.ids),
                ("state", "=", "done"),
                "|",
                ("child_transaction_ids", "=", False),
                ("source_transaction_id", "!=", False),
            ],
            groupby=["provider_id", "currency_id"],
            aggregates=["amount:sum"],
        )
        currency_total_by_provider = {provider: [] for provider in self}
        for provider, currency, subtotal in transaction_data:
            currency_total_by_provider[provider].append((currency, subtotal))

        # Convert per-currency amounts and sum them
        today = fields.Date.today()
        for provider in self:
            processed_amount = 0
            for currency, currency_total in currency_total_by_provider[provider]:
                target_currency = provider.main_currency_id
                processed_amount += currency._convert(
                    currency_total, target_currency, company=provider.company_id, date=today
                )
            provider.processed_amount = processed_amount

    @api.depends("payment_transaction_ids")
    def _compute_transaction_count(self):
        transaction_data = self.env["payment.transaction"]._read_group(
            [("provider_id", "in", self.ids)], ["provider_id"], ["__count"]
        )
        provider_data = {provider.id: count for provider, count in transaction_data}
        for provider in self:
            provider.transaction_count = provider_data.get(provider.id, 0)

    @api.depends("payment_token_ids")
    def _compute_token_count(self):
        token_data = self.env["payment.token"]._read_group(
            [("provider_id", "in", self.ids)], ["provider_id"], ["__count"]
        )
        provider_data = {provider.id: count for provider, count in token_data}
        for provider in self:
            provider.token_count = provider_data.get(provider.id, 0)

    @api.depends("code")
    def _compute_feature_support_fields(self):
        """Compute the feature support fields based on the provider.

        Feature support fields are used to specify which additional features are supported by a
        given provider. These fields are as follows:

        - `support_express_checkout`: Whether the "express checkout" feature is supported. `False`
          by default.
        - `support_manual_capture`: Whether the "manual capture" feature is supported. `False` by
          default.
        - `support_refund`: Which type of the "refunds" feature is supported: `None`,
          `'full_only'`, or `'partial'`. `None` by default.
        - `support_tokenization`: Whether the "tokenization feature" is supported. `False` by
          default.

        For a provider to specify that it supports additional features, it must override this method
        and set the related feature support fields to the desired value on the appropriate
        `payment.provider` records.

        :return: None
        """
        self.update({
            "support_express_checkout": None,
            "support_manual_capture": None,
            "support_tokenization": None,
            "support_refund": "none",
        })

    @api.depends("code")
    def _compute_available_currency_ids(self):
        """Compute the available currencies based on their support by the providers.

        If the provider does not filter out any currency, the field is left empty for UX reasons.

        :return: None
        """
        all_currencies = self.env["res.currency"].with_context(active_test=False).search([])
        for provider in self:
            supported_currencies = provider._get_supported_currencies()
            if supported_currencies < all_currencies:  # Some currencies have been filtered out.
                provider.available_currency_ids = supported_currencies
            else:
                provider.available_currency_ids = None

    def _get_supported_currencies(self):
        """Return the supported currencies for the payment provider.

        By default, all currencies are considered supported, including the inactive ones. For a
        provider to filter out specific currencies, it must override this method and return the
        subset of supported currencies.

        Note: `self.ensure_one()`

        :return: The supported currencies.
        :rtype: res.currency
        """
        self.ensure_one()
        return self.env["res.currency"].with_context(active_test=False).search([])

    # === ONCHANGE METHODS === #

    @api.onchange("is_live")
    def _onchange_is_live_toggle_is_published(self):
        """Publish or unpublish the provider when the live mode is toggled.

        :return: None
        """
        self.is_published = self.is_live

    @api.onchange("is_live")
    def _onchange_is_live_warn_before_disabling_tokens(self):
        """Warn the user that tokens linked to the provider get archived when live mode is toggled.

        :return: A client action with the warning message, if any.
        :rtype: dict
        """
        if self.token_count:
            return {
                "warning": {
                    "title": self.env._("Warning"),
                    "message": self.env._(
                        "This action will also archive %s tokens that are registered with this"
                        " provider.",
                        self.token_count,
                    ),
                }
            }

    @api.onchange("company_id")
    def _onchange_company_block_if_existing_transactions(self):
        """Raise a user error when the company is changed and linked transactions exist.

        :return: None
        :raise UserError: If transactions are linked to the provider.
        """
        different_company = self._origin.company_id != self.company_id
        if different_company and self.env["payment.transaction"].search_count(
            [("provider_id", "=", self._origin.id)], limit=1
        ):
            raise UserError(
                self.env._(
                    "You cannot change the company of a payment provider"
                    " with existing transactions."
                )
            )

    # === CONSTRAINT METHODS === #

    @api.constrains("capture_manually")
    def _check_manual_capture_supported_by_payment_methods(self):
        if self.capture_manually:
            incompatible_pms = self.payment_method_ids.filtered(
                lambda method: (
                    method.active
                    and not method.primary_payment_method_id
                    and method.support_manual_capture == "none"
                )
            )
            if incompatible_pms:
                raise ValidationError(
                    self.env._(
                        "The following payment methods must be disabled in order to enable manual"
                        " capture: %s",
                        ", ".join(incompatible_pms.mapped("name")),
                    )
                )

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        providers = super().create(vals_list)
        providers._check_required_if_provider()
        return providers

    def write(self, vals):
        # Determine which providers are affected by each side effect
        live_mode_toggling = (
            self.filtered(lambda p: p.is_live != vals["is_live"])
            if "is_live" in vals
            else self.browse()
        )
        being_archived = self.filtered("active") if vals.get("active") is False else self.browse()
        being_unarchived = (
            self.filtered(lambda p: not p.active) if vals.get("active") is True else self.browse()
        )

        result = super().write(vals)

        # Apply the side-effects to related records
        (live_mode_toggling | being_archived)._archive_linked_tokens()
        being_archived.payment_method_ids.active = False
        being_unarchived._activate_default_pms()

        # Run checks
        self._check_required_if_provider()

        return result

    def _check_required_if_provider(self):
        """Check that provider-specific required fields have been filled.

        The fields that have the `required_if_provider='<provider_code>'` attribute are required
        for all `payment.provider` records with the `code` field equal to `<provider_code>` that are
        in live mode.

        Provider-specific views should make the form fields required under the same conditions.

        :return: None
        :raise ValidationError: If a provider-specific required field is empty.
        """
        field_names = []
        for field_name, field in self._fields.items():
            required_for_provider_code = getattr(field, "required_if_provider", None)
            if required_for_provider_code and any(
                required_for_provider_code == provider._get_code() and not provider[field_name]
                for provider in self.filtered("is_live")
            ):
                ir_field = self.env["ir.model.fields"]._get(self._name, field_name)
                field_names.append(ir_field.field_description)
        if field_names:
            raise ValidationError(
                self.env._("The following fields must be filled: %s", ", ".join(field_names))
            )

    def _archive_linked_tokens(self):
        """Archive all the payment tokens of the providers.

        :return: None
        """
        self.env["payment.token"].search([("provider_id", "in", self.ids)]).write({"active": False})

    def _activate_default_pms(self):
        """Activate the default payment methods of the provider.

        :return: None
        """
        # Filter out pms that are not compatible with manual capture if the provider requires it
        compatible_primary_pms = self.primary_payment_method_ids.filtered(
            lambda pm: pm.support_manual_capture != "none" or not pm.provider_id.capture_manually
        )
        # Activate primary PMs listed as default for their own provider and all their brands
        primary_pms_to_activate = compatible_primary_pms.filtered(
            lambda pm: pm.code in pm.provider_id._get_default_payment_method_codes()
        )
        (primary_pms_to_activate + primary_pms_to_activate.brand_ids).active = True

    def _get_default_payment_method_codes(self):
        """Return the default payment methods for this provider.

        Note: `self.ensure_one()`

        :return: The default payment method codes.
        :rtype: set
        """
        self.ensure_one()
        return set()

    def copy(self, default=None):
        """Override of `base` to copy the payment methods linked to the providers."""
        new_providers = super().copy(default=default)
        for src_provider, new_provider in zip(self, new_providers):
            src_primary_pms = src_provider.payment_method_ids.filtered("is_primary")
            new_primary_pms = src_primary_pms.copy({"provider_id": new_provider.id})
            for src_primary_pm, new_primary_pm in zip(src_primary_pms, new_primary_pms):
                src_primary_pm.brand_ids.copy({
                    "provider_id": new_provider.id,
                    "primary_payment_method_id": new_primary_pm.id,
                })
        return new_providers

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for provider, vals in zip(self, vals_list):
            if "name" not in default and "company_id" not in default:
                vals["name"] = provider.env._("%s (copy)", provider.name)
        return vals_list

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        """Prevent the deletion of the payment provider if it has an xmlid."""
        external_ids = self.get_external_id()
        for provider in self:
            external_id = external_ids[provider.id]
            if external_id and not external_id.startswith("__export__"):
                raise UserError(
                    provider.env._(
                        "You cannot delete the payment provider %s; archive or uninstall it"
                        " instead.",
                        provider.name,
                    )
                )

    # === ACTION METHODS === #

    def button_immediate_install(self):
        """Install the module and reload the page.

        Note: `self.ensure_one()`

        :return: The action to reload the page.
        :rtype: dict
        """
        if self.module_id and self.module_state != "installed":
            self.module_id.button_immediate_install()
            return {"type": "ir.actions.client", "tag": "reload"}

    def action_start_onboarding(self, menu_id=None):  # noqa: ARG002
        """Start the provider-specific onboarding.

        Providers implementing a specific onboarding must override this method and return the action
        to run the onboarding.

        :param int menu_id: The menu from which the onboarding is started, as an `ir.ui.menu` id.
        :return: The onboarding action.
        :rtype: dict
        """
        return {}

    def action_reset_credentials(self):
        """Reset the credentials of the provider, disable it, and unpublish it.

        Note: self.ensure_one()

        :return: The result of the write operation.
        :rtype: bool
        """
        self.ensure_one()
        return self.write({"is_published": False, **self._get_reset_values()})

    def _get_reset_values(self):
        """Return the values to reset the credentials of the provider.

        Providers can override this to supply their own credential fields to reset.

        Note: self.ensure_one() from :meth: `action_reset_credentials`

        :return: The values to reset the credentials of the provider.
        :rtype: dict
        """
        return {}

    def action_add_payment_method(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "payment.method",
            "view_mode": "form",
            "context": {
                "default_provider_id": self.id,
                "default_sequence": 1,
                "default_active": True,
            },
            "target": "new",
        }

    def action_toggle_is_published(self):
        """Toggle the field `is_published`.

        :return: None
        :raise UserError: If the provider is disabled.
        """
        self.is_published = not self.is_published

    def action_view_payment_transactions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Payment Transactions"),
            "res_model": "payment.transaction",
            "view_mode": "list,form",
            "domain": [("id", "in", self.payment_transaction_ids.ids)],
            "context": {"create": False},
        }

    def action_view_payment_tokens(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Payment Tokens"),
            "res_model": "payment.token",
            "view_mode": "list,form",
            "domain": [("id", "in", self.with_context(active_test=False).payment_token_ids.ids)],
            "context": {"create": False},
        }

    # === BUSINESS METHODS === #

    @api.model
    def _find_available_providers(
        self,
        company_id,
        partner_id,
        amount,
        *,
        currency_id=None,
        force_tokenization=False,
        is_express_checkout=False,
        is_validation=False,
        report=None,
        **kwargs,
    ):
        """Find the providers available for the given payment context.

        :param int company_id: The company to which providers must belong, as a `res.company` id
        :param int partner_id: The partner making the payment, as a `res.partner` id
        :param float amount: The amount to pay (`0` for validation transactions)
        :param int currency_id: The payment currency, as a `res.currency` id
        :param bool force_tokenization: Whether providers must allow tokenization
        :param bool is_express_checkout: Whether providers must allow express checkout
        :param bool is_validation: Whether the operation is a validation
        :param dict report: The report into which availability statuses are to be logged
        :param dict kwargs: Forwarded to `_is_tokenization_required` and available to overrides
        :return: The available providers
        :rtype: payment.provider
        """
        # Search available providers with the base domain
        providers = self.env["payment.provider"].search([
            "|",
            ("module_state", "=", "installed"),
            ("module_id", "=", False),
            *self.env["payment.provider"]._check_company_domain(company_id),
        ])
        payment_utils.add_to_report(report, providers)

        # Filter by `is_published` state
        if not self.env.user._is_internal():
            providers = providers.filtered("is_published")

        # Handle the partner country; allow all countries if the list is empty
        partner = self.env["res.partner"].browse(partner_id)
        if partner.country_id:  # The partner country must either not be set or be supported
            unfiltered_providers = providers
            providers = providers.filtered(
                lambda p: (
                    not p.available_country_ids
                    or partner.country_id.id in p.available_country_ids.ids
                )
            )
            payment_utils.add_to_report(
                report,
                unfiltered_providers - providers,
                available=False,
                reason=REPORT_REASONS_MAPPING["incompatible_country"],
            )

        # Handle the available currencies; allow all currencies if the list is empty
        currency = self.env["res.currency"].browse(currency_id).exists()
        if currency:
            unfiltered_providers = providers
            providers = providers.filtered(
                lambda p: (
                    not p.available_currency_ids or currency.id in p.available_currency_ids.ids
                )
            )
            payment_utils.add_to_report(
                report,
                unfiltered_providers - providers,
                available=False,
                reason=REPORT_REASONS_MAPPING["incompatible_currency"],
            )

        # Handle the minimum and maximum amounts
        if not is_validation and currency:  # The currency is required to convert the amount
            company = self.env["res.company"].browse(company_id).exists()
            converted_amount = currency._convert(amount, company.currency_id, company)
            unfiltered_providers = providers
            providers = providers.filtered(
                lambda p: (
                    (
                        not p.minimum_amount
                        or currency.compare_amounts(p.minimum_amount, converted_amount) != 1
                    )
                    and (
                        not p.maximum_amount
                        or currency.compare_amounts(p.maximum_amount, converted_amount) != -1
                    )
                )
            )
            payment_utils.add_to_report(
                report,
                unfiltered_providers - providers,
                available=False,
                reason=REPORT_REASONS_MAPPING["exceed_min_or_max_amount"],
            )

        # Handle tokenization support requirements
        if force_tokenization or self._is_tokenization_required(**kwargs):
            unfiltered_providers = providers
            providers = providers.filtered("allow_tokenization")
            payment_utils.add_to_report(
                report,
                unfiltered_providers - providers,
                available=False,
                reason=REPORT_REASONS_MAPPING["tokenization_not_supported"],
            )

        # Handle express checkout
        if is_express_checkout:
            unfiltered_providers = providers
            providers = providers.filtered("allow_express_checkout")
            payment_utils.add_to_report(
                report,
                unfiltered_providers - providers,
                available=False,
                reason=REPORT_REASONS_MAPPING["express_checkout_not_supported"],
            )

        return providers

    def _is_tokenization_required(self, **_kwargs):
        """Return whether tokenizing the transaction is required given its context.

        For a module to make the tokenization required based on the payment context, it must
        override this method and return whether it is required.

        :param dict _kwargs: The payment context
        :return: Whether tokenizing the transaction is required
        :rtype: bool
        """
        return False

    def _find_available_payment_methods(
        self,
        partner_id,
        *,
        currency_id=None,
        force_tokenization=False,
        is_express_checkout=False,
        report=None,
        **_kwargs,
    ):
        """Find the providers' payment methods available for the given payment context.

        :param int partner_id: The partner making the payment, as a `res.partner` id
        :param int currency_id: The payment currency, as a `res.currency` id
        :param bool force_tokenization: Whether payment methods must support tokenization
        :param bool is_express_checkout: Whether payment methods must support express checkout
        :param dict report: The report into which availability statuses are to be logged
        :return: The available payment methods
        :rtype: payment.method
        """
        payment_methods = self.primary_payment_method_ids.filtered("active")
        payment_utils.add_to_report(report, payment_methods)

        # Handle the partner country; allow all countries if the list is empty
        partner = self.env["res.partner"].browse(partner_id)
        if partner.country_id:  # The partner country must either not be set or be supported
            unfiltered_pms = payment_methods
            payment_methods = payment_methods.filtered(
                lambda pm: (
                    not pm.supported_country_ids
                    or partner.country_id.id in pm.supported_country_ids.ids
                )
            )
            payment_utils.add_to_report(
                report,
                unfiltered_pms - payment_methods,
                available=False,
                reason=REPORT_REASONS_MAPPING["incompatible_country"],
            )

        # Handle the supported currencies; allow all currencies if the list is empty
        if currency_id:
            unfiltered_pms = payment_methods
            payment_methods = payment_methods.filtered(
                lambda pm: (
                    not pm.supported_currency_ids or currency_id in pm.supported_currency_ids.ids
                )
            )
            payment_utils.add_to_report(
                report,
                unfiltered_pms - payment_methods,
                available=False,
                reason=REPORT_REASONS_MAPPING["incompatible_currency"],
            )

        # Handle tokenization support requirements
        if force_tokenization:
            unfiltered_pms = payment_methods
            payment_methods = payment_methods.filtered("support_tokenization")
            payment_utils.add_to_report(
                report,
                unfiltered_pms - payment_methods,
                available=False,
                reason=REPORT_REASONS_MAPPING["tokenization_not_supported"],
            )

        # Handle express checkout
        if is_express_checkout:
            unfiltered_pms = payment_methods
            payment_methods = payment_methods.filtered("support_express_checkout")
            payment_utils.add_to_report(
                report,
                unfiltered_pms - payment_methods,
                available=False,
                reason=REPORT_REASONS_MAPPING["express_checkout_not_supported"],
            )

        return payment_methods

    def _find_available_tokens(self, partner_id, **_kwargs):
        """Find the providers' tokens available for the given payment context.

        :param int partner_id: The partner making the payment, as a `res.partner` id
        :return: The available tokens
        :rtype: payment.token
        """
        return self.env["payment.token"].search([
            ("provider_id", "in", self.ids),
            ("partner_id", "=", partner_id),
        ])

    def _get_validation_amount(self):
        """Return the amount to use for validation operations.

        For a provider to support tokenization, it must override this method and return the
        validation amount. If it is `0`, it is not necessary to create the override.

        Note: `self.ensure_one()`

        :return: The validation amount.
        :rtype: float
        """
        self.ensure_one()
        return 0.0

    def _get_validation_currency(self):
        """Return the currency to use for validation operations.

        The validation currency must be supported by both the provider and the payment method. If
        the payment method is not passed, only the provider's supported currencies are considered.
        If no suitable currency is found, the provider's company's currency is returned instead.

        For a provider to support tokenization and specify a different validation currency, it must
        override this method and return the appropriate validation currency.

        Note: `self.ensure_one()`

        :return: The validation currency.
        :rtype: recordset of `res.currency`
        """
        self.ensure_one()

        # Find the validation currency at the intersection of the provider's and payment method's
        # supported currencies. An empty recordset means that all currencies are supported.
        provider_currencies = self.available_currency_ids
        pm = self.env.context.get("validation_pm")
        pm_currencies = self.env["res.currency"] if not pm else pm.supported_currency_ids
        validation_currency = None
        if provider_currencies and pm_currencies:
            validation_currency = (provider_currencies & pm_currencies)[:1]
        elif provider_currencies and not pm_currencies:
            validation_currency = provider_currencies[:1]
        elif not provider_currencies and pm_currencies:
            validation_currency = pm_currencies[:1]
        if not validation_currency:  # All currencies are supported, or no suitable one was found.
            validation_currency = self.company_id.currency_id
        return validation_currency

    def _get_redirect_form_view(self, is_validation=False):  # noqa: ARG002
        """Return the view of the template used to render the redirect form.

        For a provider to return a different view depending on whether the operation is a
        validation, it must override this method and return the appropriate view.

        Note: `self.ensure_one()`

        :param bool is_validation: Whether the operation is a validation.
        :return: The view of the redirect form template.
        :rtype: record of `ir.ui.view`
        """
        self.ensure_one()
        return self.redirect_form_view_id

    def _get_amount_precision(self, currency, **_kwargs):
        """Return the precision of the transaction amount for the given currency.

        The precision is determined by the currency's `decimal_places` field. For a provider to
        enforce different precision, it must override this method and return the desired number of
        decimal places.

        :param recordset currency: The currency of the transaction, as a `res.currency` record.
        :return: The number of decimal places.
        :rtype: int
        """
        if not currency.name:
            return None
        return CURRENCY_MINOR_UNITS.get(currency.name, currency.decimal_places)

    # === REQUEST HELPERS === #

    def _send_api_request(
        self, method, endpoint, *, params=None, data=None, json=None, reference=None, **kwargs
    ):
        """Send a request to the API.

        Whenever possible, calls to this method should be wrapped in a try-except block to prevent
        the `ValidationError` that is raised when the request fails from bubbling up. Exceptions to
        this rule include calls from a controller that must return the error message to the client.

        Note: `self.ensure_one()`

        :param str method: The HTTP method of the request.
        :param str endpoint: The endpoint of the API to reach with the request.
        :param dict params: The query string parameters of the request.
        :param dict|str data: The body of the request.
        :param dict json: The JSON-formatted body of the request.
        :param str reference: The reference of the transaction, if any.
        :param dict kwargs: Provider-specific data forwarded to the specialized helper methods.
        :return: The formatted content of the response.
        :rtype: dict|str
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        # Build the request.
        url = self._build_request_url(endpoint, **kwargs)
        payload = params or data or json
        headers = self._build_request_headers(method, endpoint, payload, **kwargs)
        auth = self._build_request_auth(**kwargs)

        # Log the request.
        self._log_request(method, url, payload, reference=reference)

        # Send the request.
        try:
            response = requests.request(
                method,
                url,
                params=params,
                data=data,
                json=json,
                headers=headers,
                auth=auth,
                timeout=10,
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise ValidationError(
                self.env._("Could not establish the connection to the payment provider.")
            ) from None

        # Log the response.
        self._log_response(response, reference=reference)

        # Parse the response.
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            try:
                error_msg = self._parse_response_error(response)
            except requests.exceptions.JSONDecodeError:  # The provider failed to parse plain text.
                error_msg = response.text
            raise ValidationError(
                self.env._("The payment provider rejected the request.\n%s", error_msg)
            ) from None
        return self._parse_response_content(response, **kwargs)

    def _build_request_url(self, endpoint, **_kwargs):  # noqa: ARG002
        """Build the URL of the request.

        This method serves as a hook to allow providers to build the request URL.

        :param str endpoint: The endpoint of the API to reach with the request.
        :param dict _kwargs: Provider-specific data.
        :return: The request URL.
        :rtype: str
        """
        return ""

    def _build_request_headers(self, method, endpoint, payload, **_kwargs):  # noqa: ARG002
        """Build the headers of the request.

        This method serves as a hook to allow providers to build the request headers.

        :param str method: The HTTP method of the request.
        :param str endpoint: The endpoint of the API to reach with the request.
        :param dict payload: The payload of the request.
        :param dict _kwargs: Provider-specific data.
        :return: The request headers.
        :rtype: dict
        """
        return {}

    def _build_request_auth(self, **_kwargs):
        """Set the basic HTTP Auth of the request.

        This method serves as a hook to allow providers to build the request's basic HTTP Auth.

        :param dict _kwargs: Provider-specific data.
        :return: The basic HTTP Auth, if any.
        :rtype: tuple
        """
        return tuple()

    def _log_request(self, method, url, payload, *, reference=None):
        """Log the request.

        The transaction reference is included in the log when possible to contextualize the request.
        When the request is not linked to a transaction, the provider's id is used instead.

        :param str method: The HTTP method of the request.
        :param str url: The URL of the request.
        :param str payload: The payload of the request.
        :param str reference: The reference of the transaction, if any.
        :rtype: None
        """
        if reference:
            log_msg = "Sending %(method)s API request to %(url)s for transaction %(ref)s."
            log_values = {"method": method, "url": url, "ref": reference}
        else:
            log_msg = "Sending %(method)s API request to %(url)s for provider %(p_id)s."
            log_values = {"method": method, "url": url, "p_id": self.id}

        # Add the payload to the log if any.
        if payload:
            log_msg += " Payload:\n%(payload)s"
            log_values["payload"] = pformat(payload)

        _logger.info(log_msg, log_values)

    def _log_response(self, response, *, reference=None):
        """Log the response.

        The transaction reference is included in the log when possible to contextualize the
        response. When the response is not linked to a transaction, the provider's id is used
        instead.

        :param requests.Response response: The response to log.
        :param str reference: The reference of the transaction, if any.
        :rtype: None
        """
        if reference:
            log_msg = (
                "Received HTTP %(code)s %(status)s API response from %(url)s for transaction"
                " %(ref)s.\n%(data)s"
            )
        else:
            log_msg = (
                "Received HTTP %(code)s %(status)s API response from %(url)s for provider %(p_id)s."
                "\n%(data)s"
            )
        log_values = {
            "code": response.status_code,
            "status": response.reason,
            "url": response.url,
            "ref": reference,
            "p_id": self.id,
            "data": response.text,
        }
        if response.ok:
            _logger.info(log_msg, log_values)
        else:
            _logger.error(log_msg, log_values)

    def _parse_response_content(self, response, **_kwargs):
        """Retrieve the JSON-formatted content of the response.

        This method serves as a hook to allow providers to parse the response content.

        :param requests.Response response: The response to parse.
        :param dict _kwargs: Provider-specific data.
        :return: The response content.
        :rtype: dict
        """
        return response.json()

    def _parse_response_error(self, response):
        """Retrieve the error message from the response.

        This method serves as a hook to allow providers to parse the response's error message.

        :param requests.Response response: The response to parse.
        :return: The error message.
        :rtype: str
        """
        return response.text

    # === SETUP METHODS === #

    @api.model
    def _setup_provider(self, provider_code, **kwargs):
        """Perform module-specific and multi-company setup steps for the provider.

        This method is called after the module of a provider is installed, with its code passed as
        `provider_code`.

        :param str provider_code: The code of the provider to setup.
        :return: None
        """
        existing_providers = self.search(self._get_provider_domain(provider_code, **kwargs))
        main_provider = existing_providers[:1]

        # Activate default PMs on install
        main_provider._activate_default_pms()

        # Duplicate providers in existing companies
        existing_provider_companies = existing_providers.company_id
        companies_needing_provider = self.env["res.company"].search([
            ("id", "not in", existing_provider_companies.ids),
            ("parent_id", "=", False),
        ])
        for company in companies_needing_provider:
            main_provider.copy({"company_id": company.id})

        # Enable the post-processing cron if still deactivated
        self._toggle_post_processing_cron()

    @api.model
    def _remove_provider(self, provider_code, **kwargs):
        """Remove the module-specific data of the given provider.

        :param str provider_code: The code of the provider whose data to remove.
        :return: None
        """
        providers = self.search(self._get_provider_domain(provider_code, **kwargs))
        providers.write(self._get_removal_values())

        # Deactivate all PMs on uninstall
        providers.payment_method_ids.active = False

        # Disable the post-processing cron if the last provider is uninstalled
        providers._toggle_post_processing_cron()

    @api.model
    def _get_provider_domain(self, provider_code, **_kwargs):
        """Return the payment provider domain.

        :param str provider_code: The code of the provider to search for.
        :param dict _kwargs: Additional keyword arguments.
        :return: The domain to search for the provider.
        :rtype: list[tuple]
        """
        return [("code", "=", provider_code)]

    def _get_removal_values(self):
        """Return the values to update a provider with when its module is uninstalled.

        For a module to specify additional removal values, it must override this method and complete
        the generic values with its specific values.

        :return: The removal values to update the removed provider with.
        :rtype: dict
        """
        return {
            "code": "none",
            "is_live": False,
            "is_published": False,
            "redirect_form_view_id": None,
            "inline_form_view_id": None,
            "token_inline_form_view_id": None,
            "express_checkout_form_view_id": None,
        }

    @api.model
    def _toggle_post_processing_cron(self):
        """Enable the post-processing cron if some providers are installed; disable it otherwise.

        This allows for saving resources on the cron's wake-up overhead when it has nothing to do.

        :return: None
        """
        post_processing_cron = self.env.ref(
            "payment.cron_post_process_payment_tx", raise_if_not_found=False
        )
        if post_processing_cron:
            any_installed_provider = bool(
                self.sudo().search_count(
                    [("module_state", "in", ("installed", "to install"))], limit=1
                )
            )
            post_processing_cron.active = any_installed_provider

    def _get_code(self):
        """Return the code of the provider.

        Note: `self.ensure_one()`

        :return: The code of the provider.
        :rtype: str
        """
        self.ensure_one()
        return self.code

    def _get_pm_from_code(self, generic_code, mapping=None):
        """Return the payment method with the given code linked to the provider.

        If a mapping is given, the search uses the generic payment method code that corresponds to
        the given provider-specific code.

        :param str generic_code: The provider-specific code of the payment method to get
        :param dict mapping: A non-exhaustive mapping of generic payment method codes to
                             provider-specific codes
        :return: The matching payment method, if any
        :rtype: payment.method
        """
        self.ensure_one()

        generic_to_specific_mapping = mapping or {}
        specific_to_generic_mapping = {v: k for k, v in generic_to_specific_mapping.items()}
        generic_code = specific_to_generic_mapping.get(generic_code, generic_code)
        return self.payment_method_ids.filtered(lambda pm: pm.code == generic_code)
