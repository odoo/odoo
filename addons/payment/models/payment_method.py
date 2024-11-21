# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import REPORT_REASONS_MAPPING


class PaymentMethod(models.Model):
    _name = 'payment.method'
    _description = "Payment Method"
    _order = 'active desc, sequence, name'

    name = fields.Char(string="Name", required=True, translate=True)
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
        string="Tokenization",
        help="Tokenization is the process of saving the payment details as a token that can later"
             " be reused without having to enter the payment details again.",
    )
    support_express_checkout = fields.Boolean(
        string="Express Checkout",
        help="Express checkout allows customers to pay faster by using a payment method that"
             " provides all required billing and shipping information, thus allowing to skip the"
             " checkout process.",
    )
    support_refund = fields.Selection(
        string="Refund",
        help="Refund is a feature allowing to refund customers directly from the payment in Odoo.",
        selection=[
            ('none', "Unsupported"),
            ('full_only', "Full Only"),
            ('partial', "Full & Partial"),
        ],
        required=True,
        default='none',
    )
    supported_country_ids = fields.Many2many(
        string="Countries",
        comodel_name='res.country',
        help="The list of countries in which this payment method can be used (if the provider"
             " allows it). In other countries, this payment method is not available to customers."
    )
    supported_currency_ids = fields.Many2many(
        string="Currencies",
        comodel_name='res.currency',
        help="The list of currencies for that are supported by this payment method (if the provider"
             " allows it). When paying with another currency, this payment method is not available "
             "to customers.",
        context={'active_test': False},
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

    @api.onchange('active', 'provider_ids', 'support_tokenization')
    def _onchange_warn_before_disabling_tokens(self):
        """ Display a warning about the consequences of archiving the payment method, detaching it
        from a provider, or removing its support for tokenization.

        Let the user know that the related tokens will be archived.

        :return: A client action with the warning message, if any.
        :rtype: dict
        """
        disabling = self._origin.active and not self.active
        detached_providers = self._origin.provider_ids.filtered(
            lambda p: p.id not in self.provider_ids.ids
        )  # Cannot use recordset difference operation because self.provider_ids is a set of NewIds.
        blocking_tokenization = self._origin.support_tokenization and not self.support_tokenization
        if disabling or detached_providers or blocking_tokenization:
            related_tokens = self.env['payment.token'].with_context(active_test=True).search(
                expression.AND([
                    [('payment_method_id', 'in', (self._origin + self._origin.brand_ids).ids)],
                    [('provider_id', 'in', detached_providers.ids)] if detached_providers else [],
                ])
            )  # Fix `active_test` in the context forwarded by the view.
            if related_tokens:
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _(
                            "This action will also archive %s tokens that are registered with this "
                            "payment method.", len(related_tokens)
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
        # Handle payment methods being archived, detached from providers, or blocking tokenization.
        archiving = values.get('active') is False
        detached_provider_ids = [
            vals[0] for command, *vals in values['provider_ids'] if command == Command.UNLINK
        ] if 'provider_ids' in values else []
        blocking_tokenization = values.get('support_tokenization') is False
        if archiving or detached_provider_ids or blocking_tokenization:
            linked_tokens = self.env['payment.token'].with_context(active_test=True).search(
                expression.AND([
                    [('payment_method_id', 'in', (self + self.brand_ids).ids)],
                    [('provider_id', 'in', detached_provider_ids)] if detached_provider_ids else [],
                ])
            )  # Fix `active_test` in the context forwarded by the view.
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
        is_express_checkout=False, report=None, **kwargs
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
        :param dict report: The report in which each provider's availability status and reason must
                            be logged.
        :param dict kwargs: Optional data. This parameter is not used here.
        :return: The compatible payment methods.
        :rtype: payment.method
        """
        # Search compatible payment methods with the base domain.
        payment_methods = self.env['payment.method'].search([('is_primary', '=', True)])
        payment_utils.add_to_report(report, payment_methods)

        # Filter by compatible providers.
        unfiltered_pms = payment_methods
        payment_methods = payment_methods.filtered(
            lambda pm: any(p in provider_ids for p in pm.provider_ids.ids)
        )
        payment_utils.add_to_report(
            report,
            unfiltered_pms - payment_methods,
            available=False,
            reason=REPORT_REASONS_MAPPING['provider_not_available'],
        )

        # Handle the partner country; allow all countries if the list is empty.
        partner = self.env['res.partner'].browse(partner_id)
        if partner.country_id:  # The partner country must either not be set or be supported.
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
                reason=REPORT_REASONS_MAPPING['incompatible_country'],
            )

        # Handle the supported currencies; allow all currencies if the list is empty.
        if currency_id:
            unfiltered_pms = payment_methods
            payment_methods = payment_methods.filtered(
                lambda pm: (
                    not pm.supported_currency_ids
                    or currency_id in pm.supported_currency_ids.ids
                )
            )
            payment_utils.add_to_report(
                report,
                unfiltered_pms - payment_methods,
                available=False,
                reason=REPORT_REASONS_MAPPING['incompatible_currency'],
            )

        # Handle tokenization support requirements.
        if force_tokenization:
            unfiltered_pms = payment_methods
            payment_methods = payment_methods.filtered('support_tokenization')
            payment_utils.add_to_report(
                report,
                unfiltered_pms - payment_methods,
                available=False,
                reason=REPORT_REASONS_MAPPING['tokenization_not_supported'],
            )

        # Handle express checkout.
        if is_express_checkout:
            unfiltered_pms = payment_methods
            payment_methods = payment_methods.filtered('support_express_checkout')
            payment_utils.add_to_report(
                report,
                unfiltered_pms - payment_methods,
                available=False,
                reason=REPORT_REASONS_MAPPING['express_checkout_not_supported'],
            )

        return payment_methods

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
