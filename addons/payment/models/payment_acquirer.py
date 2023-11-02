# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _name = 'payment.acquirer'
    _description = 'Payment Acquirer'
    _order = 'module_state, state desc, sequence, name'

    def _valid_field_parameter(self, field, name):
        return name == 'required_if_provider' or super()._valid_field_parameter(field, name)

    # Configuration fields
    name = fields.Char(string="Name", required=True, translate=True)
    sequence = fields.Integer(string="Sequence", help="Define the display order")
    provider = fields.Selection(
        string="Provider", help="The Payment Service Provider to use with this acquirer",
        selection=[('none', "No Provider Set")], default='none', required=True)
    state = fields.Selection(
        string="State",
        help="In test mode, a fake payment is processed through a test payment interface.\n"
             "This mode is advised when setting up the acquirer.",
        selection=[('disabled', "Disabled"), ('enabled', "Enabled"), ('test', "Test Mode")],
        default='disabled', required=True, copy=False)
    company_id = fields.Many2one(  # Indexed to speed-up ORM searches (from ir_rule or others)
        string="Company", comodel_name='res.company', default=lambda self: self.env.company.id,
        required=True, index=True)
    payment_icon_ids = fields.Many2many(
        string="Supported Payment Icons", comodel_name='payment.icon')
    allow_tokenization = fields.Boolean(
        string="Allow Saving Payment Methods",
        help="This controls whether customers can save their payment methods as payment tokens.\n"
             "A payment token is an anonymous link to the payment method details saved in the\n"
             "acquirer's database, allowing the customer to reuse it for a next purchase.")
    capture_manually = fields.Boolean(
        string="Capture Amount Manually",
        help="Capture the amount from Odoo, when the delivery is completed.\n"
             "Use this if you want to charge your customers cards only when\n"
             "you are sure you can ship the goods to them.")
    redirect_form_view_id = fields.Many2one(
        string="Redirect Form Template", comodel_name='ir.ui.view',
        help="The template rendering a form submitted to redirect the user when making a payment",
        domain=[('type', '=', 'qweb')])
    inline_form_view_id = fields.Many2one(
        string="Inline Form Template", comodel_name='ir.ui.view',
        help="The template rendering the inline payment form when making a direct payment",
        domain=[('type', '=', 'qweb')])
    country_ids = fields.Many2many(
        string="Countries", comodel_name='res.country', relation='payment_country_rel',
        column1='payment_id', column2='country_id',
        help="The countries for which this payment acquirer is available.\n"
             "If none is set, it is available for all countries.")
    journal_id = fields.Many2one(
        string="Payment Journal", comodel_name='account.journal',
        compute='_compute_journal_id', inverse='_inverse_journal_id',
        help="The journal in which the successful transactions are posted",
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]")

    # Fees fields
    fees_active = fields.Boolean(string="Add Extra Fees")
    fees_dom_fixed = fields.Float(string="Fixed domestic fees")
    fees_dom_var = fields.Float(string="Variable domestic fees (in percents)")
    fees_int_fixed = fields.Float(string="Fixed international fees")
    fees_int_var = fields.Float(string="Variable international fees (in percents)")

    # Message fields
    display_as = fields.Char(
        string="Displayed as", help="Description of the acquirer for customers",
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
    support_authorization = fields.Boolean(string="Authorize Mechanism Supported")
    support_fees_computation = fields.Boolean(string="Fees Computation Supported")
    support_tokenization = fields.Boolean(string="Tokenization Supported")
    support_refund = fields.Selection(
        string="Type of Refund Supported",
        selection=[('full_only', "Full Only"), ('partial', "Partial")],
    )

    # Kanban view fields
    description = fields.Html(
        string="Description", help="The description shown in the card in kanban view ")
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
    show_payment_icon_ids = fields.Boolean(compute='_compute_view_configuration_fields')
    show_pre_msg = fields.Boolean(compute='_compute_view_configuration_fields')
    show_pending_msg = fields.Boolean(compute='_compute_view_configuration_fields')
    show_auth_msg = fields.Boolean(compute='_compute_view_configuration_fields')
    show_done_msg = fields.Boolean(compute='_compute_view_configuration_fields')
    show_cancel_msg = fields.Boolean(compute='_compute_view_configuration_fields')

    #=== COMPUTE METHODS ===#

    @api.depends('state', 'module_state')
    def _compute_color(self):
        """ Update the color of the kanban card based on the state of the acquirer.

        :return: None
        """
        for acquirer in self:
            if acquirer.module_id and not acquirer.module_state == 'installed':
                acquirer.color = 4  # blue
            elif acquirer.state == 'disabled':
                acquirer.color = 3  # yellow
            elif acquirer.state == 'test':
                acquirer.color = 2  # orange
            elif acquirer.state == 'enabled':
                acquirer.color = 7  # green

    @api.depends('provider')
    def _compute_view_configuration_fields(self):
        """ Compute view configuration fields based on the provider.

        By default, all fields are set to `True`.
        For an acquirer to hide generic elements (pages, fields) in a view, it must override this
        method and set their corresponding view configuration field to `False`.

        :return: None
        """
        self.update({
            'show_credentials_page': True,
            'show_allow_tokenization': True,
            'show_payment_icon_ids': True,
            'show_pre_msg': True,
            'show_pending_msg': True,
            'show_auth_msg': True,
            'show_done_msg': True,
            'show_cancel_msg': True,
        })

    def _compute_journal_id(self):
        for acquirer in self:
            payment_method = self.env['account.payment.method.line'].search([
                ('journal_id.company_id', '=', acquirer.company_id.id),
                ('code', '=', acquirer.provider)
            ], limit=1)
            if payment_method:
                acquirer.journal_id = payment_method.journal_id
            else:
                acquirer.journal_id = False

    def _inverse_journal_id(self):
        for acquirer in self:
            payment_method_line = self.env['account.payment.method.line'].search([
                ('journal_id.company_id', '=', acquirer.company_id.id),
                ('code', '=', acquirer.provider)
            ], limit=1)
            if acquirer.journal_id:
                if not payment_method_line:
                    default_payment_method_id = acquirer._get_default_payment_method_id()
                    existing_payment_method_line = self.env['account.payment.method.line'].search([
                        ('payment_method_id', '=', default_payment_method_id),
                        ('journal_id', '=', acquirer.journal_id.id)
                    ], limit=1)
                    if not existing_payment_method_line:
                        self.env['account.payment.method.line'].create({
                            'payment_method_id': default_payment_method_id,
                            'journal_id': acquirer.journal_id.id,
                        })
                else:
                    payment_method_line.journal_id = acquirer.journal_id
            elif payment_method_line:
                payment_method_line.unlink()

    def _get_default_payment_method_id(self):
        self.ensure_one()
        return self.env.ref('account.account_payment_method_manual_in').id

    #=== CONSTRAINT METHODS ===#

    @api.constrains('fees_dom_var', 'fees_int_var')
    def _check_fee_var_within_boundaries(self):
        """ Check that variable fees are within realistic boundaries.

        Variable fees values should always be positive and below 100% to respectively avoid negative
        and infinite (division by zero) fees amount.

        :return None
        """
        for acquirer in self:
            if any(not 0 <= fee < 100 for fee in (acquirer.fees_dom_var, acquirer.fees_int_var)):
                raise ValidationError(_("Variable fees must always be positive and below 100%."))

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, values_list):
        acquirers = super().create(values_list)
        acquirers._check_required_if_provider()
        return acquirers

    def write(self, values):
        result = super().write(values)
        self._check_required_if_provider()
        return result

    def _check_required_if_provider(self):
        """ Check that acquirer-specific required fields have been filled.

        The fields that have the `required_if_provider="<provider>"` attribute are made required
        for all payment.acquirer records with the `provider` field equal to <provider> and with the
        `state` field equal to 'enabled' or 'test'.
        Acquirer-specific views should make the form fields required under the same conditions.

        :return: None
        :raise ValidationError: if an acquirer-specific required field is empty
        """
        field_names = []
        enabled_acquirers = self.filtered(lambda acq: acq.state in ['enabled', 'test'])
        for name, field in self._fields.items():
            required_provider = getattr(field, 'required_if_provider', None)
            if required_provider and any(
                required_provider == acquirer.provider and not acquirer[name]
                for acquirer in enabled_acquirers
            ):
                ir_field = self.env['ir.model.fields']._get(self._name, name)
                field_names.append(ir_field.field_description)
        if field_names:
            raise ValidationError(
                _("The following fields must be filled: %s", ", ".join(field_names))
            )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        """ Prevent the deletion of the payment acquirer if it has an xmlid. """
        external_ids = self.get_external_id()
        for acquirer in self:
            external_id = external_ids[acquirer.id]
            if external_id and not external_id.startswith('__export__'):
                raise UserError(_(
                    "You cannot delete the payment acquirer %s; disable it or uninstall it instead.",
                    acquirer.name,
                ))

    #=== ACTION METHODS ===#

    def button_immediate_install(self):
        """ Install the acquirer's module and reload the page.

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

    #=== BUSINESS METHODS ===#

    @api.model
    def _get_compatible_acquirers(
        self, company_id, partner_id, currency_id=None, force_tokenization=False,
        is_validation=False, **kwargs
    ):
        """ Select and return the acquirers matching the criteria.

        The base criteria are that acquirers must not be disabled, be in the company that is
        provided, and support the country of the partner if it exists.

        :param int company_id: The company to which acquirers must belong, as a `res.company` id
        :param int partner_id: The partner making the payment, as a `res.partner` id
        :param int currency_id: The payment currency if known beforehand, as a `res.currency` id
        :param bool force_tokenization: Whether only acquirers allowing tokenization can be matched
        :param bool is_validation: Whether the operation is a validation
        :param dict kwargs: Optional data. This parameter is not used here
        :return: The compatible acquirers
        :rtype: recordset of `payment.acquirer`
        """
        # Compute the base domain for compatible acquirers
        domain = ['&', ('state', 'in', ['enabled', 'test']), ('company_id', '=', company_id)]

        # Handle partner country
        partner = self.env['res.partner'].browse(partner_id)
        if partner.country_id:  # The partner country must either not be set or be supported
            domain = expression.AND([
                domain,
                ['|', ('country_ids', '=', False), ('country_ids', 'in', [partner.country_id.id])]
            ])

        # Handle tokenization support requirements
        if force_tokenization or self._is_tokenization_required(**kwargs):
            domain = expression.AND([domain, [('allow_tokenization', '=', True)]])

        compatible_acquirers = self.env['payment.acquirer'].search(domain)
        return compatible_acquirers

    @api.model
    def _is_tokenization_required(self, provider=None, **kwargs):
        """ Return whether tokenizing the transaction is required given its context.

        For a module to make the tokenization required based on the transaction context, it must
        override this method and return whether it is required.

        :param str provider: The provider of the acquirer handling the transaction
        :param dict kwargs: The transaction context. This parameter is not used here
        :return: Whether tokenizing the transaction is required
        :rtype: bool
        """
        return False

    def _should_build_inline_form(self, is_validation=False):
        """ Return whether the inline form should be instantiated if it exists.

        For an acquirer to handle both direct payments and payment with redirection, it should
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

        For an acquirer to base the computation on different variables, or to use a different
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

        For an acquirer to support tokenization, it must override this method and return the amount
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

        For an acquirer to support tokenization, it must override this method and return the
        currency to be used in a payment method validation operation *if the validation amount is
        not null*.

        Note: self.ensure_one()

        :return: The validation currency
        :rtype: recordset of `res.currency`
        """
        self.ensure_one()
        return self.journal_id.currency_id or self.company_id.currency_id

    def _get_redirect_form_view(self, is_validation=False):
        """ Return the view of the template used to render the redirect form.

        For an acquirer to return a different view depending on whether the operation is a
        validation, it must override this method and return the appropriate view.

        Note: self.ensure_one()

        :param bool is_validation: Whether the operation is a validation
        :return: The redirect form template
        :rtype: record of `ir.ui.view`
        """
        self.ensure_one()
        return self.redirect_form_view_id
