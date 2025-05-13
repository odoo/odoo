# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PaymentToken(models.Model):
    _name = 'payment.token'
    _order = 'partner_id, id desc'
    _description = 'Payment Token'
    _check_company_auto = True

    provider_id = fields.Many2one(string="Provider", comodel_name='payment.provider', required=True)
    provider_code = fields.Selection(string="Provider Code", related='provider_id.code')
    company_id = fields.Many2one(
        related='provider_id.company_id', store=True, index=True
    )  # Indexed to speed-up ORM searches (from ir_rule or others).
    payment_method_id = fields.Many2one(
        string="Payment Method", comodel_name='payment.method', readonly=True, required=True
    )
    payment_method_code = fields.Char(
        string="Payment Method Code", related='payment_method_id.code'
    )
    payment_details = fields.Char(
        string="Payment Details", help="The clear part of the payment method's payment details.",
    )
    partner_id = fields.Many2one(string="Partner", comodel_name='res.partner', required=True, index=True)
    provider_ref = fields.Char(
        string="Provider Reference",
        help="The provider reference of the token of the transaction.",
        required=True,
    )  # This is not the same thing as the provider reference of the transaction.
    transaction_ids = fields.One2many(
        string="Payment Transactions", comodel_name='payment.transaction', inverse_name='token_id'
    )
    active = fields.Boolean(string="Active", default=True)

    # === COMPUTE METHODS === #

    @api.depends('payment_details', 'create_date')
    def _compute_display_name(self):
        for token in self:
            token.display_name = token._build_display_name()

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'provider_id' in values:
                provider = self.env['payment.provider'].browse(values['provider_id'])

                # Include provider-specific create values
                values.update(self._get_specific_create_values(provider.code, values))
            else:
                pass  # Let psycopg warn about the missing required field.

        return super().create(vals_list)

    @api.model
    def _get_specific_create_values(self, provider_code, values):
        """ Complete the values of the `create` method with provider-specific values.

        For a provider to add its own create values, it must overwrite this method and return a
        dict of values. Provider-specific values take precedence over those of the dict of generic
        create values.

        :param str provider_code: The code of the provider managing the token.
        :param dict values: The original create values.
        :return: The dict of provider-specific create values.
        :rtype: dict
        """
        return dict()

    def write(self, vals):
        """ Prevent unarchiving tokens and handle their archiving.

        :return: The result of the call to the parent method.
        :rtype: bool
        :raise UserError: If at least one token is being unarchived.
        """
        if 'active' in vals:
            if vals['active']:
                if any(
                    not token.payment_method_id.active
                    or token.provider_id.state == 'disabled'
                    for token in self
                ):
                    raise UserError(_(
                        "You can't unarchive tokens linked to inactive payment methods or disabled"
                        " providers."
                    ))
            else:
                # Call the handlers in sudo mode because this method might have been called by RPC.
                self.filtered('active').sudo()._handle_archiving()

        return super().write(vals)

    @api.constrains('partner_id')
    def _check_partner_is_never_public(self):
        """ Check that the partner associated with the token is never public. """
        for token in self:
            if token.partner_id.is_public:
                raise ValidationError(_("No token can be assigned to the public partner."))

    def _handle_archiving(self):
        """ Handle the archiving of tokens.

        For a module to perform additional operations when a token is archived, it must override
        this method.

        :return: None
        """
        return

    # === BUSINESS METHODS === #

    def _get_available_tokens(self, providers_ids, partner_id, is_validation=False, **kwargs):
        """ Return the available tokens linked to the given providers and partner.

        For a module to retrieve the available tokens, it must override this method and add
        information in the kwargs to define the context of the request.

        :param list providers_ids: The ids of the providers available for the transaction.
        :param int partner_id: The id of the partner.
        :param bool is_validation: Whether the transaction is a validation operation.
        :param dict kwargs: Locally unused keywords arguments.
        :return: The available tokens.
        :rtype: payment.token
        """
        if not is_validation:
            return self.env['payment.token'].search(
                [('provider_id', 'in', providers_ids), ('partner_id', '=', partner_id)]
            )
        else:
            # Get all the tokens of the partner and of their commercial partner, regardless of
            # whether the providers are available.
            partner = self.env['res.partner'].browse(partner_id)
            return self.env['payment.token'].search(
                [('partner_id', 'in', [partner.id, partner.commercial_partner_id.id])]
            )

    def _build_display_name(self, *args, max_length=34, should_pad=True, **kwargs):
        """ Build a token name of the desired maximum length with the format `•••• 1234`.

        The payment details are padded on the left with up to four padding characters. The padding
        is only added if there is enough room for it. If not, it is either reduced or not added at
        all. If there is not enough room for the payment details either, they are trimmed from the
        left.

        For a module to customize the display name of a token, it must override this method and
        return the customized display name.

        Note: `self.ensure_one()`

        :param list args: The arguments passed by QWeb when calling this method.
        :param int max_length: The desired maximum length of the token name. The default is `34` to
                               fit the largest IBANs.
        :param bool should_pad: Whether the token should be padded.
        :param dict kwargs: Optional data used in overrides of this method.
        :return: The padded token name.
        :rtype: str
        """
        self.ensure_one()

        if not self.create_date:
            return ''

        padding_length = max_length - len(self.payment_details or '')
        if not self.payment_details:
            create_date_str = self.create_date.strftime('%Y/%m/%d')
            display_name = _("Payment details saved on %(date)s", date=create_date_str)
        elif padding_length >= 2:  # Enough room for padding.
            padding = '•' * min(padding_length - 1, 4) + ' ' if should_pad else ''
            display_name = ''.join([padding, self.payment_details])
        elif padding_length > 0:  # Not enough room for padding.
            display_name = self.payment_details
        else:  # Not enough room for neither padding nor the payment details.
            display_name = self.payment_details[-max_length:] if max_length > 0 else ''
        return display_name

    def get_linked_records_info(self):
        """ Return a list of information about records linked to the current token.

        For a module to implement payments and link documents to a token, it must override this
        method and add information about linked document records to the returned list.

        The information must be structured as a dict with the following keys:

        - `description`: The description of the record's model (e.g. "Subscription").
        - `id`: The id of the record.
        - `name`: The name of the record.
        - `url`: The url to access the record.

        Note: `self.ensure_one()`

        :return: The list of information about the linked document records.
        :rtype: list
        """
        self.ensure_one()
        return []
