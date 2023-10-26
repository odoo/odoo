# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression


class PaymentMethod(models.Model):
    _name = 'payment.method'
    _description = "Payment Method"
    _order = 'active desc, sequence, name'

    name = fields.Char(string="Name", required=True)
    code = fields.Char(
        string="Code", help="The technical code of this payment method.", required=True
    )
    sequence = fields.Integer(string="Sequence", default=1)
    primary_payment_method_id = fields.Many2one(
        string="Primary Payment Method",
        help="The primary payment method of the current payment method, if the latter is a brand."
             "\nFor example, \"Card\" is the primary payment method of the card brand \"VISA\".",
        comodel_name='payment.method',
    )
    brand_ids = fields.One2many(
        string="Brands",
        help="The brands of the payment methods that will be displayed on the payment form.",
        comodel_name='payment.method',
        inverse_name='primary_payment_method_id',
    )
    is_primary = fields.Boolean(
        string="Is Primary Payment Method",
        compute='_compute_is_primary',
        search='_search_is_primary',
    )
    provider_ids = fields.Many2many(
        string="Providers",
        help="The list of providers supporting this payment method.",
        comodel_name='payment.provider',
    )
    active = fields.Boolean(string="Active", default=True)
    image = fields.Image(
        string="Image",
        help="The base image used for this payment method; in a 64x64 px format.",
        max_width=64,
        max_height=64,
        required=True,
    )
    image_payment_form = fields.Image(
        string="The resized image displayed on the payment form.",
        related='image',
        store=True,
        max_width=45,
        max_height=30,
    )

    # Feature support fields.
    support_tokenization = fields.Boolean(
        string="Tokenization Supported",
        help="Tokenization is the process of saving the payment details as a token that can later"
             " be reused without having to enter the payment details again.",
    )
    support_express_checkout = fields.Boolean(
        string="Express Checkout Supported",
        help="Express checkout allows customers to pay faster by using a payment method that"
             " provides all required billing and shipping information, thus allowing to skip the"
             " checkout process.",
    )
    support_refund = fields.Selection(
        string="Type of Refund Supported",
        selection=[('full_only', "Full Only"), ('partial', "Partial")],
        help="Refund is a feature allowing to refund customers directly from the payment in Odoo.",
    )
    supported_country_ids = fields.Many2many(
        string="Supported Countries",
        comodel_name='res.country',
        help="The list of countries in which this payment method can be used (if the provider"
             " allows it). In other countries, this payment method is not available to customers."
    )
    supported_currency_ids = fields.Many2many(
        string="Supported Currencies",
        comodel_name='res.currency',
        help="The list of currencies for that are supported by this payment method (if the provider"
             " allows it). When paying with another currency, this payment method is not available "
             "to customers.",
    )

    #=== COMPUTE METHODS ===#

    def _compute_is_primary(self):
        for payment_method in self:
            payment_method.is_primary = not payment_method.primary_payment_method_id

    def _search_is_primary(self, operator, value):
        if operator == '=' and value is True:
            return [('primary_payment_method_id', '=', False)]
        elif operator == '=' and value is False:
            return [('primary_payment_method_id', '!=', False)]
        else:
            raise NotImplementedError(_("Operation not supported."))

    #=== ONCHANGE METHODS ===#

    @api.onchange('provider_ids')
    def _onchange_provider_ids_warn_before_disabling_tokens(self):
        """ Display a warning about the consequences of detaching a payment method from a provider.

        Let the user know that tokens related to a provider get archived if it is detached from the
        payment methods associated with those tokens.

        :return: A client action with the warning message, if any.
        :rtype: dict
        """
        detached_providers = self._origin.provider_ids.filtered(
            lambda p: p.id not in self.provider_ids.ids
        )  # Cannot use recordset difference operation because self.provider_ids is a set of NewIds.
        if detached_providers:
            related_tokens = self.env['payment.token'].with_context(active_test=True).search([
                ('payment_method_id', 'in', (self._origin + self._origin.brand_ids).ids),
                ('provider_id', 'in', detached_providers.ids),
            ])  # Fix `active_test` in the context forwarded by the view.
            if related_tokens:
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _(
                            "This action will also archive %s tokens that are registered with this "
                            "payment method. Archiving tokens is irreversible.", len(related_tokens)
                        )
                    }
                }

    @api.onchange('provider_ids')
    def _onchange_provider_ids_warn_before_attaching_payment_method(self):
        """ Display a warning before attaching a payment method to a provider.

        :return: A client action with the warning message, if any.
        :rtype: dict
        """
        attached_providers = self.provider_ids.filtered(
            lambda p: p.id.origin not in self._origin.provider_ids.ids
        )
        if attached_providers:
            return {
                'warning': {
                    'title': _("Warning"),
                    'message': _(
                        "Please make sure that %(payment_method)s is supported by %(provider)s.",
                        payment_method=self.name,
                        provider=', '.join(attached_providers.mapped('name'))
                    )
                }
            }

    #=== CRUD METHODS ===#

    def write(self, values):
        # Handle payment methods being detached from providers.
        if 'provider_ids' in values:
            detached_provider_ids = [
                vals[0] for command, *vals in values['provider_ids'] if command == Command.UNLINK
            ]
            if detached_provider_ids:
                linked_tokens = self.env['payment.token'].with_context(active_test=True).search([
                    ('provider_id', 'in', detached_provider_ids),
                    ('payment_method_id', 'in', (self + self.brand_ids).ids),
                ])  # Fix `active_test` in the context forwarded by the view.
                linked_tokens.active = False

        # Prevent enabling a payment method if it is not linked to an enabled provider.
        if values.get('active'):
            for pm in self:
                primary_pm = pm if pm.is_primary else pm.primary_payment_method_id
                if (
                    not primary_pm.active  # Don't bother for already enabled payment methods.
                    and all(p.state == 'disabled' for p in primary_pm.provider_ids)
                ):
                    raise UserError(_(
                        "This payment method needs a partner in crime; you should enable a payment"
                        " provider supporting this method first."
                    ))

        return super().write(values)

    # === BUSINESS METHODS === #

    def _get_compatible_payment_methods(
        self, provider_ids, partner_id, currency_id=None, force_tokenization=False,
        is_express_checkout=False
    ):
        """ Search and return the payment methods matching the compatibility criteria.

        The compatibility criteria are that payment methods must: be supported by at least one of
        the providers; support the country of the partner if it exists; be primary payment methods
        (not a brand). If provided, the optional keyword arguments further refine the criteria.

        :param list provider_ids: The list of providers by which the payment methods must be at
                                  least partially supported to be considered compatible, as a list
                                  of `payment.provider` ids.
        :param int partner_id: The partner making the payment, as a `res.partner` id.
        :param int currency_id: The payment currency, if known beforehand, as a `res.currency` id.
        :param bool force_tokenization: Whether only payment methods supporting tokenization can be
                                        matched.
        :param bool is_express_checkout: Whether the payment is made through express checkout.
        :return: The compatible payment methods.
        :rtype: payment.method
        """
        # Compute the base domain for compatible payment methods.
        domain = [('provider_ids', 'in', provider_ids), ('is_primary', '=', True)]

        # Handle the partner country; allow all countries if the list is empty.
        partner = self.env['res.partner'].browse(partner_id)
        if partner.country_id:  # The partner country must either not be set or be supported.
            domain = expression.AND([
                domain, [
                    '|',
                    ('supported_country_ids', '=', False),
                    ('supported_country_ids', 'in', [partner.country_id.id]),
                ]
            ])

        # Handle the supported currencies; allow all currencies if the list is empty.
        if currency_id:
            domain = expression.AND([
                domain, [
                    '|',
                    ('supported_currency_ids', '=', False),
                    ('supported_currency_ids', 'in', [currency_id]),
                ]
            ])

        # Handle tokenization support requirements.
        if force_tokenization:
            domain = expression.AND([domain, [('support_tokenization', '=', True)]])

        # Handle express checkout.
        if is_express_checkout:
            domain = expression.AND([domain, [('support_express_checkout', '=', True)]])

        # Search the payment methods matching the compatibility criteria.
        compatible_payment_methods = self.env['payment.method'].search(domain)
        return compatible_payment_methods

    def _get_from_code(self, code, mapping=None):
        """ Get the payment method corresponding to the given provider-specific code.

        If a mapping is given, the search uses the generic payment method code that corresponds to
        the given provider-specific code.

        :param str code: The provider-specific code of the payment method to get.
        :param dict mapping: A non-exhaustive mapping of generic payment method codes to
                             provider-specific codes.
        :return: The corresponding payment method, if any.
        :type: payment.method
        """
        generic_to_specific_mapping = mapping or {}
        specific_to_generic_mapping = {v: k for k, v in generic_to_specific_mapping.items()}
        return self.search([('code', '=', specific_to_generic_mapping.get(code, code))], limit=1)
