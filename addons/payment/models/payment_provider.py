# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from psycopg2 import sql

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _name = 'payment.provider'
    _description = 'Payment Provider'
    _order = 'module_state, state desc, sequence, name'

    def _valid_field_parameter(self, field, name):
        return name == 'required_if_provider' or super()._valid_field_parameter(field, name)

    # Configuration fields
    name = fields.Char(string="Name", required=True, translate=True)
    sequence = fields.Integer(string="Sequence", help="Define the display order")
    code = fields.Selection(
        string="Code", help="The Payment Service Code to use with this provider",
        selection=[('none', "No Provider Set")], default='none', required=True)
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
    payment_icon_ids = fields.Many2many(
        string="Supported Payment Icons", comodel_name='payment.icon')
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
        domain=[('type', '=', 'qweb')])
    inline_form_view_id = fields.Many2one(
        string="Inline Form Template", comodel_name='ir.ui.view',
        help="The template rendering the inline payment form when making a direct payment",
        domain=[('type', '=', 'qweb')])
    token_inline_form_view_id = fields.Many2one(
        string="Token Inline Form Template",
        comodel_name='ir.ui.view',
        help="The template rendering the inline payment form when making a payment by token.",
        domain=[('type', '=', 'qweb')],
    )
    express_checkout_form_view_id = fields.Many2one(
        string="Express Checkout Form Template",
        comodel_name='ir.ui.view',
        help="The template rendering the express payment methods' form.",
        domain=[('type', '=', 'qweb')],
    )

    # Availability fields.
    available_country_ids = fields.Many2many(
        string="Countries",
        comodel_name='res.country',
        help="The countries in which this payment provider is available. Leave blank to make it "
             "available in all countries.",
        relation='payment_country_rel',
        column1='payment_id',
        column2='country_id',
    )
    maximum_amount = fields.Monetary(
        string="Maximum Amount",
        help="The maximum payment amount that this payment provider is available for. Leave blank "
             "to make it available for any payment amount.",
        currency_field='main_currency_id',
    )

    # Fees fields
    fees_active = fields.Boolean(string="Add Extra Fees")
    fees_dom_fixed = fields.Float(string="Fixed domestic fees")
    fees_dom_var = fields.Float(string="Variable domestic fees (in percents)")
    fees_int_fixed = fields.Float(string="Fixed international fees")
    fees_int_var = fields.Float(string="Variable international fees (in percents)")

    # Message fields
    display_as = fields.Char(
        string="Displayed as", help="Description of the provider for customers",
        translate=True)
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
        default=lambda self: _("Your payment has been successfully processed. Thank you!"),
        translate=True)
    cancel_msg = fields.Html(
        string="Canceled Message",
        help="The message displayed if the order is canceled during the payment process",
        default=lambda self: _("Your payment has been cancelled."), translate=True)

    # Feature support fields
    support_tokenization = fields.Boolean(
        string="Tokenization Supported", compute='_compute_feature_support_fields'
    )
    support_manual_capture = fields.Boolean(
        string="Manual Capture Supported", compute='_compute_feature_support_fields'
    )
    support_express_checkout = fields.Boolean(
        string="Express Checkout Supported", compute='_compute_feature_support_fields'
    )
    support_refund = fields.Selection(
        string="Type of Refund Supported",
        selection=[('full_only', "Full Only"), ('partial', "Partial")],
        compute='_compute_feature_support_fields',
    )
    support_fees = fields.Boolean(
        string="Fees Supported", compute='_compute_feature_support_fields'
    )

    # Kanban view fields
    image_128 = fields.Image(string="Image", max_width=128, max_height=128)
    color = fields.Integer(
        string="Color", help="The color of the card in kanban view", compute='_compute_color',
        store=True)

    # Module-related fields
    module_id = fields.Many2one(string="Corresponding Module", comodel_name='ir.module.module')
    module_state = fields.Selection(
        string="Installation State", related='module_id.state', store=True)  # Stored for sorting
    module_to_buy = fields.Boolean(string="Odoo Enterprise Module", related='module_id.to_buy')

    # View configuration fields
    show_credentials_page = fields.Boolean(compute='_compute_view_configuration_fields')
    show_allow_tokenization = fields.Boolean(compute='_compute_view_configuration_fields')
    show_allow_express_checkout = fields.Boolean(compute='_compute_view_configuration_fields')
    show_payment_icon_ids = fields.Boolean(compute='_compute_view_configuration_fields')
    show_pre_msg = fields.Boolean(compute='_compute_view_configuration_fields')
    show_pending_msg = fields.Boolean(compute='_compute_view_configuration_fields')
    show_auth_msg = fields.Boolean(compute='_compute_view_configuration_fields')
    show_done_msg = fields.Boolean(compute='_compute_view_configuration_fields')
    show_cancel_msg = fields.Boolean(compute='_compute_view_configuration_fields')

    #=== COMPUTE METHODS ===#

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
    def _compute_view_configuration_fields(self):
        """ Compute view configuration fields based on the provider.

        By default, all fields are set to `True`.
        For a provider to hide generic elements (pages, fields) in a view, it must override this
        method and set their corresponding view configuration field to `False`.

        :return: None
        """
        self.update({
            'show_credentials_page': True,
            'show_allow_tokenization': True,
            'show_allow_express_checkout': True,
            'show_payment_icon_ids': True,
            'show_pre_msg': True,
            'show_pending_msg': True,
            'show_auth_msg': True,
            'show_done_msg': True,
            'show_cancel_msg': True,
        })

    def _compute_feature_support_fields(self):
        """ Compute the feature support fields.

        For an provider to support one or more additional feature, it must override this method.

        :return: None
        """
        self.update(dict.fromkeys((
            'support_express_checkout',
            'support_fees',
            'support_manual_capture',
            'support_refund',
            'support_tokenization',
        ), None))

    #=== ONCHANGE METHODS ===#

    @api.onchange('state')
    def _onchange_state_switch_is_published(self):
        """ Automatically publish or unpublish the provider depending on its state.

        :return: None
        """
        self.is_published = self.state == 'enabled'

    @api.onchange('state')
    def _onchange_state_warn_before_disabling_tokens(self):
        """ Display a warning about the consequences of disabling an provider.

        Let the user know that tokens related to an provider get archived if it is disabled or if
        its state is changed from 'test' to 'enabled' and vice versa.

        :return: The warning message in a client action.
        :rtype: dict
        """
        self.ensure_one()

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
                            "provider. Archiving tokens is irreversible.", len(related_tokens)
                        )
                    }
                }

    #=== CONSTRAINT METHODS ===#

    @api.constrains('fees_dom_var', 'fees_int_var')
    def _check_fee_var_within_boundaries(self):
        """ Check that variable fees are within realistic boundaries.

        Variable fees values should always be positive and below 100% to respectively avoid negative
        and infinite (division by zero) fees amount.

        :return None
        """
        for provider in self:
            if any(not 0 <= fee < 100 for fee in (provider.fees_dom_var, provider.fees_int_var)):
                raise ValidationError(_("Variable fees must always be positive and below 100%."))

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, values_list):
        providers = super().create(values_list)
        providers._check_required_if_provider()
        return providers

    def write(self, values):
        # Handle provider disabling.
        if 'state' in values:
            state_changed_providers = self.filtered(
                lambda p: p.state not in ('disabled', values['state'])
            )  # Don't handle providers being enabled or whose state is not updated.
            state_changed_providers._handle_state_change()

        result = super().write(values)
        self._check_required_if_provider()

        return result

    def _check_required_if_provider(self):
        """ Check that provider-specific required fields have been filled.

        The fields that have the `required_if_provider="<provider>"` attribute are made required
        for all payment.provider records with the `code` field equal to <provider> and with the
        `state` field equal to 'enabled' or 'test'.
        Provider-specific views should make the form fields required under the same conditions.

        :return: None
        :raise ValidationError: if a provider-specific required field is empty
        """
        field_names = []
        enabled_providers = self.filtered(lambda p: p.state in ['enabled', 'test'])
        for name, field in self._fields.items():
            required_provider = getattr(field, 'required_if_provider', None)
            if required_provider and any(
                required_provider == provider.code and not provider[name]
                for provider in enabled_providers
            ):
                ir_field = self.env['ir.model.fields']._get(self._name, name)
                field_names.append(ir_field.field_description)
        if field_names:
            raise ValidationError(
                _("The following fields must be filled: %s", ", ".join(field_names))
            )

    def _handle_state_change(self):
        """ Archive all the payment tokens linked to these providers.

        :return: None
        """
        self.env['payment.token'].search([('provider_id', 'in', self.ids)]).write({'active': False})

    #=== ACTION METHODS ===#

    def button_immediate_install(self):
        """ Install the provider's module and reload the page.

        Note: self.ensure_one()

        :return: The action to reload the page
        :rtype: dict
        """
        if self.module_id and self.module_state != 'installed':
            self.module_id.button_immediate_install()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

    def action_toggle_is_published(self):
        """ Toggle the provider's is_published state.

        :return: none
        :raise UserError: If the provider is disabled.
        """
        if self.state != 'disabled':
            self.is_published = not self.is_published
        else:
            raise UserError(_("You cannot publish a disabled provider."))

    #=== BUSINESS METHODS ===#

    @api.model
    def _get_compatible_providers(
        self, company_id, partner_id, amount, currency_id=None, force_tokenization=False,
        is_express_checkout=False, is_validation=False, **kwargs
    ):
        """ Select and return the providers matching the criteria.

        The base criteria are that providers must not be disabled, be in the company that is
        provided, and support the country of the partner if it exists.

        :param int company_id: The company to which providers must belong, as a `res.company` id
        :param int partner_id: The partner making the payment, as a `res.partner` id
        :param float amount: The amount to pay, `0` for validation transactions.
        :param int currency_id: The payment currency if known beforehand, as a `res.currency` id
        :param bool force_tokenization: Whether only providers allowing tokenization can be matched
        :param bool is_express_checkout: Whether the payment is made through express checkout.
        :param bool is_validation: Whether the operation is a validation
        :param dict kwargs: Optional data. This parameter is not used here
        :return: The compatible providers
        :rtype: recordset of `payment.provider`
        """
        # Compute the base domain for compatible providers
        domain = ['&', ('state', 'in', ['enabled', 'test']), ('company_id', '=', company_id)]

        # Handle the is_published state.
        if not self.env.user._is_internal():
            domain = expression.AND([domain, [('is_published', '=', True)]])

        # Handle partner country
        partner = self.env['res.partner'].browse(partner_id)
        if partner.country_id:  # The partner country must either not be set or be supported
            domain = expression.AND([
                domain, [
                    '|',
                    ('available_country_ids', '=', False),
                    ('available_country_ids', 'in', [partner.country_id.id]),
                ]
            ])

        # Handle the maximum amount.
        currency = self.env['res.currency'].browse(currency_id).exists()
        if not is_validation and currency:  # The currency is required to convert the amount.
            company = self.env['res.company'].browse(company_id).exists()
            date = fields.Date.context_today(self)
            converted_amount = currency._convert(amount, company.currency_id, company, date)
            domain = expression.AND([
                domain, [
                    '|', '|',
                    ('maximum_amount', '>=', converted_amount),
                    ('maximum_amount', '=', False),
                    ('maximum_amount', '=', 0.),
                ]
            ])

        # Handle tokenization support requirements
        if force_tokenization or self._is_tokenization_required(**kwargs):
            domain = expression.AND([domain, [('allow_tokenization', '=', True)]])

        # Handle express checkout.
        if is_express_checkout:
            domain = expression.AND([domain, [('allow_express_checkout', '=', True)]])

        compatible_providers = self.env['payment.provider'].search(domain)
        return compatible_providers

    def _is_tokenization_required(self, **kwargs):
        """ Return whether tokenizing the transaction is required given its context.

        For a module to make the tokenization required based on the transaction context, it must
        override this method and return whether it is required.

        :param dict kwargs: The transaction context. This parameter is not used here
        :return: Whether tokenizing the transaction is required
        :rtype: bool
        """
        return False

    def _should_build_inline_form(self, is_validation=False):
        """ Return whether the inline form should be instantiated if it exists.

        For a provider to handle both direct payments and payment with redirection, it should
        override this method and return whether the inline form should be instantiated (i.e. if the
        payment should be direct) based on the operation (online payment or validation).

        :param bool is_validation: Whether the operation is a validation
        :return: Whether the inline form should be instantiated
        :rtype: bool
        """
        return True

    def _compute_fees(self, amount, currency, country):
        """ Compute the transaction fees.

        The computation is based on the generic fields `fees_dom_fixed`, `fees_dom_var`,
        `fees_int_fixed` and `fees_int_var` and is done according to the following formula:

        `fees = (amount * variable / 100.0 + fixed) / (1 - variable / 100.0)` where the value
        of `fixed` and `variable` is taken either from the domestic (dom) or international (int)
        field depending on whether the country matches the company's country.

        For a provider to base the computation on different variables, or to use a different
        formula, it must override this method and return the resulting fees as a float.

        :param float amount: The amount to pay for the transaction
        :param recordset currency: The currency of the transaction, as a `res.currency` record
        :param recordset country: The customer country, as a `res.country` record
        :return: The computed fees
        :rtype: float
        """
        self.ensure_one()

        fees = 0.0
        if self.fees_active:
            if country == self.company_id.country_id:
                fixed = self.fees_dom_fixed
                variable = self.fees_dom_var
            else:
                fixed = self.fees_int_fixed
                variable = self.fees_int_var
            fees = (amount * variable / 100.0 + fixed) / (1 - variable / 100.0)
        return fees

    def _get_validation_amount(self):
        """ Get the amount to transfer in a payment method validation operation.

        For a provider to support tokenization, it must override this method and return the amount
        to be transferred in a payment method validation operation *if the validation amount is not
        null*.

        Note: self.ensure_one()

        :return: The validation amount
        :rtype: float
        """
        self.ensure_one()
        return 0.0

    def _get_validation_currency(self):
        """ Get the currency of the transfer in a payment method validation operation.

        For a provider to support tokenization, it must override this method and return the
        currency to be used in a payment method validation operation *if the validation amount is
        not null*.

        Note: self.ensure_one()

        :return: The validation currency
        :rtype: recordset of `res.currency`
        """
        self.ensure_one()
        return self.company_id.currency_id

    def _get_redirect_form_view(self, is_validation=False):
        """ Return the view of the template used to render the redirect form.

        For a provider to return a different view depending on whether the operation is a
        validation, it must override this method and return the appropriate view.

        Note: self.ensure_one()

        :param bool is_validation: Whether the operation is a validation
        :return: The redirect form template
        :rtype: record of `ir.ui.view`
        """
        self.ensure_one()
        return self.redirect_form_view_id

    @api.model
    def _setup_provider(self, provider_code):
        """ Prepare module-specific data for a given provider.

        This method is called after a new provider module is installed and also for all existing
        providers when `account_payment` is installed.

        :param str provider_code: The code of the provider to setup.
        :return: None
        """

    @api.model
    def _remove_provider(self, provider_code):
        """ Clean module-specific data for a given provider.

        :param str provider_code: The code of the provider to setup.
        :return: None
        """
        providers = self.search([('provider', '=', provider_code)])
        providers.write({
            'provider': 'none',
            'state': 'disabled',
        })

    def _neutralize(self):
        super()._neutralize()
        self.flush_model()
        self.invalidate_model()
        self.env.cr.execute("""
            UPDATE payment_provider SET state = 'disabled'
            WHERE state NOT IN ('test', 'disabled')
        """)

    def _neutralize_fields(self, provider, fields):
        """ Helper to neutralize API keys for a specific provider
        :param str provider: name of provider
        :param list fields: list of fields to nullify
        """
        self.flush_model()
        self.invalidate_model()
        query = sql.SQL("""
            UPDATE payment_provider
            SET ({fields}) = ROW({vals})
            WHERE code = %s
        """).format(fields=sql.SQL(','.join(fields)), vals=sql.SQL(', '.join(['NULL'] * len(fields))))
        self.env.cr.execute(query, (provider, ))
