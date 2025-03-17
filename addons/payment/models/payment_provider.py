# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import REPORT_REASONS_MAPPING

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _name = 'payment.provider'
    _description = 'Payment Provider'
    _order = 'module_state, state desc, sequence, name'
    _check_company_auto = True

    def _valid_field_parameter(self, field, name):
        return name == 'required_if_provider' or super()._valid_field_parameter(field, name)

    # Configuration fields
    name = fields.Char(string="Name", required=True, translate=True)
    sequence = fields.Integer(string="Sequence", help="Define the display order")
    code = fields.Selection(
        string="Code",
        help="The technical code of this payment provider.",
        selection=[('none', "No Provider Set")],
        default='none',
        required=True,
    )
    state = fields.Selection(
        string="State",
        help="In test mode, a fake payment is processed through a test payment interface.\n"
             "This mode is advised when setting up the provider.",
        selection=[('disabled', "Disabled"), ('enabled', "Enabled"), ('test', "Test Mode")],
        default='disabled', required=True, copy=False)
    is_published = fields.Boolean(
        string="Published",
        help="Whether the provider is visible on the website or not. Tokens remain functional but "
             "are only visible on manage forms.",
    )
    company_id = fields.Many2one(  # Indexed to speed-up ORM searches (from ir_rule or others)
        string="Company", comodel_name='res.company', default=lambda self: self.env.company.id,
        required=True, index=True)
    main_currency_id = fields.Many2one(
        related='company_id.currency_id',
        help="The main currency of the company, used to display monetary fields.",
    )
    payment_method_ids = fields.Many2many(
        string="Supported Payment Methods", comodel_name='payment.method'
    )
    allow_tokenization = fields.Boolean(
        string="Allow Saving Payment Methods",
        help="This controls whether customers can save their payment methods as payment tokens.\n"
             "A payment token is an anonymous link to the payment method details saved in the\n"
             "provider's database, allowing the customer to reuse it for a next purchase.")
    capture_manually = fields.Boolean(
        string="Capture Amount Manually",
        help="Capture the amount from Odoo, when the delivery is completed.\n"
             "Use this if you want to charge your customers cards only when\n"
             "you are sure you can ship the goods to them.")
    allow_express_checkout = fields.Boolean(
        string="Allow Express Checkout",
        help="This controls whether customers can use express payment methods. Express checkout "
             "enables customers to pay with Google Pay and Apple Pay from which address "
             "information is collected at payment.",
    )
    redirect_form_view_id = fields.Many2one(
        string="Redirect Form Template", comodel_name='ir.ui.view',
        help="The template rendering a form submitted to redirect the user when making a payment",
        domain=[('type', '=', 'qweb')],
        ondelete='restrict',
    )
    inline_form_view_id = fields.Many2one(
        string="Inline Form Template", comodel_name='ir.ui.view',
        help="The template rendering the inline payment form when making a direct payment",
        domain=[('type', '=', 'qweb')],
        ondelete='restrict',
    )
    token_inline_form_view_id = fields.Many2one(
        string="Token Inline Form Template",
        comodel_name='ir.ui.view',
        help="The template rendering the inline payment form when making a payment by token.",
        domain=[('type', '=', 'qweb')],
        ondelete='restrict',
    )
    express_checkout_form_view_id = fields.Many2one(
        string="Express Checkout Form Template",
        comodel_name='ir.ui.view',
        help="The template rendering the express payment methods' form.",
        domain=[('type', '=', 'qweb')],
        ondelete='restrict',
    )

    # Availability fields
    available_country_ids = fields.Many2many(
        string="Countries",
        comodel_name='res.country',
        help="The countries in which this payment provider is available. Leave blank to make it "
             "available in all countries.",
        relation='payment_country_rel',
        column1='payment_id',
        column2='country_id',
    )
    available_currency_ids = fields.Many2many(
        string="Currencies",
        help="The currencies available with this payment provider. Leave empty not to restrict "
             "any.",
        comodel_name='res.currency',
        relation='payment_currency_rel',
        column1="payment_provider_id",
        column2="currency_id",
        compute='_compute_available_currency_ids',
        store=True,
        readonly=False,
        context={'active_test': False},
    )
    maximum_amount = fields.Monetary(
        string="Maximum Amount",
        help="The maximum payment amount that this payment provider is available for. Leave blank "
             "to make it available for any payment amount.",
        currency_field='main_currency_id',
    )

    # Message fields
    pre_msg = fields.Html(
        string="Help Message", help="The message displayed to explain and help the payment process",
        translate=True)
    pending_msg = fields.Html(
        string="Pending Message",
        help="The message displayed if the order pending after the payment process",
        default=lambda self: _(
            "Your payment has been successfully processed but is waiting for approval."
        ), translate=True)
    auth_msg = fields.Html(
        string="Authorize Message", help="The message displayed if payment is authorized",
        default=lambda self: _("Your payment has been authorized."), translate=True)
    done_msg = fields.Html(
        string="Done Message",
        help="The message displayed if the order is successfully done after the payment process",
        default=lambda self: _("Your payment has been successfully processed."),
        translate=True)
    cancel_msg = fields.Html(
        string="Cancelled Message",
        help="The message displayed if the order is cancelled during the payment process",
        default=lambda self: _("Your payment has been cancelled."), translate=True)

    # Feature support fields
    support_tokenization = fields.Boolean(
        string="Tokenization", compute='_compute_feature_support_fields'
    )
    support_manual_capture = fields.Selection(
        string="Manual Capture Supported",
        selection=[('full_only', "Full Only"), ('partial', "Partial")],
        compute='_compute_feature_support_fields',
    )
    support_express_checkout = fields.Boolean(
        string="Express Checkout", compute='_compute_feature_support_fields'
    )
    support_refund = fields.Selection(
        string="Refund",
        help="Refund is a feature allowing to refund customers directly from the payment in Odoo.",
        selection=[
            ('none', "Unsupported"),
            ('full_only', "Full Only"),
            ('partial', "Full & Partial"),
        ],
        compute='_compute_feature_support_fields',
    )

    # Kanban view fields
    image_128 = fields.Image(string="Image", max_width=128, max_height=128)
    color = fields.Integer(
        string="Color", help="The color of the card in kanban view", compute='_compute_color',
        store=True)

    # Module-related fields
    module_id = fields.Many2one(string="Corresponding Module", comodel_name='ir.module.module')
    module_state = fields.Selection(string="Installation State", related='module_id.state')
    module_to_buy = fields.Boolean(string="Odoo Enterprise Module", related='module_id.to_buy')

    #=== COMPUTE METHODS ===#

    @api.depends('code')
    def _compute_available_currency_ids(self):
        """ Compute the available currencies based on their support by the providers.

        If the provider does not filter out any currency, the field is left empty for UX reasons.

        :return: None
        """
        all_currencies = self.env['res.currency'].with_context(active_test=False).search([])
        for provider in self:
            supported_currencies = provider._get_supported_currencies()
            if supported_currencies < all_currencies:  # Some currencies have been filtered out.
                provider.available_currency_ids = supported_currencies
            else:
                provider.available_currency_ids = None

    @api.depends('state', 'module_state')
    def _compute_color(self):
        """ Update the color of the kanban card based on the state of the provider.

        :return: None
        """
        for provider in self:
            if provider.module_id and not provider.module_state == 'installed':
                provider.color = 4  # blue
            elif provider.state == 'disabled':
                provider.color = 3  # yellow
            elif provider.state == 'test':
                provider.color = 2  # orange
            elif provider.state == 'enabled':
                provider.color = 7  # green

    @api.depends('code')
    def _compute_feature_support_fields(self):
        """ Compute the feature support fields based on the provider.

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
            'support_express_checkout': None,
            'support_manual_capture': None,
            'support_tokenization': None,
            'support_refund': 'none',
        })

    #=== ONCHANGE METHODS ===#

    @api.onchange('state')
    def _onchange_state_switch_is_published(self):
        """ Automatically publish or unpublish the provider depending on its state.

        :return: None
        """
        self.is_published = self.state == 'enabled'

    @api.onchange('state')
    def _onchange_state_warn_before_disabling_tokens(self):
        """ Display a warning about the consequences of disabling a provider.

        Let the user know that tokens related to a provider get archived if it is disabled or if its
        state is changed from 'test' to 'enabled', and vice versa.

        :return: A client action with the warning message, if any.
        :rtype: dict
        """
        if self._origin.state in ('test', 'enabled') and self._origin.state != self.state:
            related_tokens = self.env['payment.token'].search(
                [('provider_id', '=', self._origin.id)]
            )
            if related_tokens:
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _(
                            "This action will also archive %s tokens that are registered with this "
                            "provider. ", len(related_tokens)
                        )
                    }
                }

    @api.onchange('company_id')
    def _onchange_company_block_if_existing_transactions(self):
        """ Raise a user error when the company is changed and linked transactions exist.

        :return: None
        :raise UserError: If transactions are linked to the provider.
        """
        if self._origin.company_id != self.company_id and self.env['payment.transaction'].search_count(
            [('provider_id', '=', self._origin.id)], limit=1
        ):
            raise UserError(_(
                "You cannot change the company of a payment provider with existing transactions."
            ))

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, values_list):
        providers = super().create(values_list)
        providers._check_required_if_provider()
        if any(provider.state != 'disabled' for provider in providers):
            self._toggle_post_processing_cron()
        return providers

    def write(self, values):
        # Handle provider state changes.
        deactivated_providers = self.env['payment.provider']
        activated_providers = self.env['payment.provider']
        if 'state' in values:
            state_changed_providers = self.filtered(
                lambda p: p.state not in ('disabled', values['state'])
            )  # Don't handle providers being enabled or whose state is not updated.
            state_changed_providers._archive_linked_tokens()
            if values['state'] == 'disabled':
                deactivated_providers = state_changed_providers
            else:  # 'enabled' or 'test'
                activated_providers = self.filtered(lambda p: p.state == 'disabled')

        result = super().write(values)
        self._check_required_if_provider()

        deactivated_providers._deactivate_unsupported_payment_methods()
        activated_providers._activate_default_pms()
        if activated_providers or deactivated_providers:
            self._toggle_post_processing_cron()

        return result

    def _check_required_if_provider(self):
        """ Check that provider-specific required fields have been filled.

        The fields that have the `required_if_provider='<provider_code>'` attribute are made
        required for all `payment.provider` records with the `code` field equal to `<provider_code>`
        and with the `state` field equal to `'enabled'` or `'test'`.

        Provider-specific views should make the form fields required under the same conditions.

        :return: None
        :raise ValidationError: If a provider-specific required field is empty.
        """
        field_names = []
        enabled_providers = self.filtered(lambda p: p.state in ['enabled', 'test'])
        for field_name, field in self._fields.items():
            required_for_provider_code = getattr(field, 'required_if_provider', None)
            if required_for_provider_code and any(
                required_for_provider_code == provider._get_code() and not provider[field_name]
                for provider in enabled_providers
            ):
                ir_field = self.env['ir.model.fields']._get(self._name, field_name)
                field_names.append(ir_field.field_description)
        if field_names:
            raise ValidationError(
                _("The following fields must be filled: %s", ", ".join(field_names))
            )

    @api.model
    def _toggle_post_processing_cron(self):
        """ Enable the post-processing cron if some providers are enabled; disable it otherwise.

        This allows for saving resources on the cron's wake-up overhead when it has nothing to do.

        :return: None
        """
        post_processing_cron = self.env.ref(
            'payment.cron_post_process_payment_tx', raise_if_not_found=False
        )
        if post_processing_cron:
            any_active_provider = bool(
                self.sudo().search_count([('state', '!=', 'disabled')], limit=1)
            )
            post_processing_cron.active = any_active_provider

    def _archive_linked_tokens(self):
        """ Archive all the payment tokens linked to the providers.

        :return: None
        """
        self.env['payment.token'].search([('provider_id', 'in', self.ids)]).write({'active': False})

    def _deactivate_unsupported_payment_methods(self):
        """ Deactivate payment methods linked to only disabled providers.

        :return: None
        """
        unsupported_pms = self.payment_method_ids.filtered(
            lambda pm: all(p.state == 'disabled' for p in pm.provider_ids)
        )
        (unsupported_pms + unsupported_pms.brand_ids).active = False

    def _activate_default_pms(self):
        """ Activate the default payment methods of the provider.

        :return: None
        """
        for provider in self:
            pm_codes = provider._get_default_payment_method_codes()
            pms = provider.with_context(active_test=False).payment_method_ids
            (pms + pms.brand_ids).filtered(lambda pm: pm.code in pm_codes).active = True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        """ Prevent the deletion of the payment provider if it has an xmlid. """
        external_ids = self.get_external_id()
        for provider in self:
            external_id = external_ids[provider.id]
            if external_id and not external_id.startswith('__export__'):
                raise UserError(_(
                    "You cannot delete the payment provider %s; disable it or uninstall it"
                    " instead.", provider.name
                ))

    #=== ACTION METHODS ===#

    def button_immediate_install(self):
        """ Install the module and reload the page.

        Note: `self.ensure_one()`

        :return: The action to reload the page.
        :rtype: dict
        """
        if self.module_id and self.module_state != 'installed':
            self.module_id.button_immediate_install()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

    def action_toggle_is_published(self):
        """ Toggle the field `is_published`.

        :return: None
        :raise UserError: If the provider is disabled.
        """
        if self.state != 'disabled':
            self.is_published = not self.is_published
        else:
            raise UserError(_("You cannot publish a disabled provider."))

    def action_view_payment_methods(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Payment Methods"),
            'res_model': 'payment.method',
            'view_mode': 'list,kanban,form',
            'domain': [('id', 'in', self.with_context(active_test=False).payment_method_ids.ids)],
            'context': {'active_test': False, 'create': False},
        }

    #=== BUSINESS METHODS ===#

    @api.model
    def _get_compatible_providers(
        self, company_id, partner_id, amount, currency_id=None, force_tokenization=False,
        is_express_checkout=False, is_validation=False, report=None, **kwargs
    ):
        """ Search and return the providers matching the compatibility criteria.

        The compatibility criteria are that providers must: not be disabled; be in the company that
        is provided; support the country of the partner if it exists; be compatible with the
        currency if provided. If provided, the optional keyword arguments further refine the
        criteria.

        :param int company_id: The company to which providers must belong, as a `res.company` id.
        :param int partner_id: The partner making the payment, as a `res.partner` id.
        :param float amount: The amount to pay. `0` for validation transactions.
        :param int currency_id: The payment currency, if known beforehand, as a `res.currency` id.
        :param bool force_tokenization: Whether only providers allowing tokenization can be matched.
        :param bool is_express_checkout: Whether the payment is made through express checkout.
        :param bool is_validation: Whether the operation is a validation.
        :param dict report: The report in which each provider's availability status and reason must
                            be logged.
        :param dict kwargs: Optional data. This parameter is not used here.
        :return: The compatible providers.
        :rtype: payment.provider
        """
        # Search compatible providers with the base domain.
        providers = self.env['payment.provider'].search([
            *self.env['payment.provider']._check_company_domain(company_id),
            ('state', 'in', ['enabled', 'test']),
        ])
        payment_utils.add_to_report(report, providers)

        # Filter by `is_published` state.
        if not self.env.user._is_internal():
            providers = providers.filtered('is_published')

        # Handle the partner country; allow all countries if the list is empty.
        partner = self.env['res.partner'].browse(partner_id)
        if partner.country_id:  # The partner country must either not be set or be supported.
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
                reason=REPORT_REASONS_MAPPING['incompatible_country'],
            )

        # Handle the maximum amount.
        currency = self.env['res.currency'].browse(currency_id).exists()
        if not is_validation and currency:  # The currency is required to convert the amount.
            company = self.env['res.company'].browse(company_id).exists()
            date = fields.Date.context_today(self)
            converted_amount = currency._convert(amount, company.currency_id, company, date)
            unfiltered_providers = providers
            providers = providers.filtered(
                lambda p: (
                    not p.maximum_amount
                    or currency.compare_amounts(p.maximum_amount, converted_amount) != -1
                )
            )
            payment_utils.add_to_report(
                report,
                unfiltered_providers - providers,
                available=False,
                reason=REPORT_REASONS_MAPPING['exceed_max_amount'],
            )

        # Handle the available currencies; allow all currencies if the list is empty.
        if currency:
            unfiltered_providers = providers
            providers = providers.filtered(
                lambda p: (
                    not p.available_currency_ids
                    or currency.id in p.available_currency_ids.ids
                )
            )
            payment_utils.add_to_report(
                report,
                unfiltered_providers - providers,
                available=False,
                reason=REPORT_REASONS_MAPPING['incompatible_currency'],
            )

        # Handle tokenization support requirements.
        if force_tokenization or self._is_tokenization_required(**kwargs):
            unfiltered_providers = providers
            providers = providers.filtered('allow_tokenization')
            payment_utils.add_to_report(
                report,
                unfiltered_providers - providers,
                available=False,
                reason=REPORT_REASONS_MAPPING['tokenization_not_supported'],
            )

        # Handle express checkout.
        if is_express_checkout:
            unfiltered_providers = providers
            providers = providers.filtered('allow_express_checkout')
            payment_utils.add_to_report(
                report,
                unfiltered_providers - providers,
                available=False,
                reason=REPORT_REASONS_MAPPING['express_checkout_not_supported'],
            )

        return providers

    def _get_supported_currencies(self):
        """ Return the supported currencies for the payment provider.

        By default, all currencies are considered supported, including the inactive ones. For a
        provider to filter out specific currencies, it must override this method and return the
        subset of supported currencies.

        Note: `self.ensure_one()`

        :return: The supported currencies.
        :rtype: res.currency
        """
        self.ensure_one()
        return self.env['res.currency'].with_context(active_test=False).search([])

    def _is_tokenization_required(self, **kwargs):
        """ Return whether tokenizing the transaction is required given its context.

        For a module to make the tokenization required based on the payment context, it must
        override this method and return whether it is required.

        :param dict kwargs: The payment context. This parameter is not used here.
        :return: Whether tokenizing the transaction is required.
        :rtype: bool
        """
        return False

    def _should_build_inline_form(self, is_validation=False):
        """ Return whether the inline payment form should be instantiated.

        For a provider to handle both direct payments and payments with redirection, it must
        override this method and return whether the inline payment form should be instantiated (i.e.
        if the payment should be direct) based on the operation (online payment or validation).

        :param bool is_validation: Whether the operation is a validation.
        :return: Whether the inline form should be instantiated.
        :rtype: bool
        """
        return True

    def _get_validation_amount(self):
        """ Return the amount to use for validation operations.

        For a provider to support tokenization, it must override this method and return the
        validation amount. If it is `0`, it is not necessary to create the override.

        Note: `self.ensure_one()`

        :return: The validation amount.
        :rtype: float
        """
        self.ensure_one()
        return 0.0

    def _get_validation_currency(self):
        """ Return the currency to use for validation operations.

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
        pm = self.env.context.get('validation_pm')
        pm_currencies = self.env['res.currency'] if not pm else pm.supported_currency_ids
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

    def _get_redirect_form_view(self, is_validation=False):
        """ Return the view of the template used to render the redirect form.

        For a provider to return a different view depending on whether the operation is a
        validation, it must override this method and return the appropriate view.

        Note: `self.ensure_one()`

        :param bool is_validation: Whether the operation is a validation.
        :return: The view of the redirect form template.
        :rtype: record of `ir.ui.view`
        """
        self.ensure_one()
        return self.redirect_form_view_id

    @api.model
    def _setup_provider(self, provider_code):
        """ Perform module-specific setup steps for the provider.

        This method is called after the module of a provider is installed, with its code passed as
        `provider_code`.

        :param str provider_code: The code of the provider to setup.
        :return: None
        """
        return

    @api.model
    def _get_removal_domain(self, provider_code, **kwargs):
        return [('code', '=', provider_code)]

    @api.model
    def _remove_provider(self, provider_code, **kwargs):
        """ Remove the module-specific data of the given provider.

        :param str provider_code: The code of the provider whose data to remove.
        :return: None
        """
        providers = self.search(self._get_removal_domain(provider_code, **kwargs))
        providers.write(self._get_removal_values())

    def _get_removal_values(self):
        """ Return the values to update a provider with when its module is uninstalled.

        For a module to specify additional removal values, it must override this method and complete
        the generic values with its specific values.

        :return: The removal values to update the removed provider with.
        :rtype: dict
        """
        return {
            'code': 'none',
            'state': 'disabled',
            'is_published': False,
            'redirect_form_view_id': None,
            'inline_form_view_id': None,
            'token_inline_form_view_id': None,
            'express_checkout_form_view_id': None,
        }

    def _get_provider_name(self):
        """ Return the translated name of the provider.

        Note: self.ensure_one()

        :return: The translated name of the provider.
        :rtype: str
        """
        self.ensure_one()
        return dict(self._fields['code']._description_selection(self.env))[self.code]

    def _get_code(self):
        """ Return the code of the provider.

        Note: self.ensure_one()

        :return: The code of the provider.
        :rtype: str
        """
        self.ensure_one()
        return self.code

    def _get_default_payment_method_codes(self):
        """ Return the default payment methods for this provider.

        Note: self.ensure_one()

        :return: The default payment method codes.
        :rtype: set
        """
        self.ensure_one()
        return set()
