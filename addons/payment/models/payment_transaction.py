# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import unicodedata
from datetime import datetime

import psycopg2
from dateutil import relativedelta
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import email_normalize_all, float_round

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import SENSITIVE_KEYS
from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__, sensitive_keys=SENSITIVE_KEYS)


class PaymentTransaction(models.Model):
    _name = 'payment.transaction'
    _description = 'Payment Transaction'
    _order = 'id desc'
    _rec_name = 'reference'

    @api.model
    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    provider_id = fields.Many2one(
        string="Provider", comodel_name='payment.provider', readonly=True, required=True
    )
    provider_code = fields.Selection(string="Provider Code", related='provider_id.code')
    company_id = fields.Many2one(  # Indexed to speed-up ORM searches (from ir_rule or others)
        related='provider_id.company_id', store=True, index=True
    )
    payment_method_id = fields.Many2one(
        string="Payment Method", comodel_name='payment.method', readonly=True, required=True
    )
    payment_method_code = fields.Char(
        string="Payment Method Code", related='payment_method_id.code'
    )
    primary_payment_method_id = fields.Many2one(
        string="Primary Payment Method",
        comodel_name='payment.method',
        compute='_compute_primary_payment_method_id',
    )
    reference = fields.Char(
        string="Reference", help="The internal reference of the transaction", readonly=True,
        required=True)  # Already has an index from the UNIQUE SQL constraint.
    provider_reference = fields.Char(
        string="Provider Reference", help="The provider reference of the transaction",
        readonly=True)  # This is not the same thing as the provider reference of the token.
    amount = fields.Monetary(
        string="Amount", currency_field='currency_id', readonly=True, required=True)
    currency_id = fields.Many2one(
        string="Currency", comodel_name='res.currency', readonly=True, required=True)
    token_id = fields.Many2one(
        string="Payment Token", comodel_name='payment.token', readonly=True, index='btree_not_null',
        domain='[("provider_id", "=", "provider_id")]', ondelete='restrict')
    state = fields.Selection(
        string="Status",
        selection=[('draft', "Draft"), ('pending', "Pending"), ('authorized', "Authorized"),
                   ('done', "Confirmed"), ('cancel', "Canceled"), ('error', "Error")],
        default='draft', readonly=True, required=True, copy=False, index=True)
    state_message = fields.Text(
        string="Message", help="The complementary information message about the state",
        readonly=True)
    last_state_change = fields.Datetime(
        string="Last State Change Date", readonly=True, default=fields.Datetime.now)

    # Fields used for traceability.
    operation = fields.Selection(  # This should not be trusted if the state is draft or pending.
        string="Operation",
        selection=[
            ('online_redirect', "Online payment with redirection"),
            ('online_direct', "Online direct payment"),
            ('online_token', "Online payment by token"),
            ('validation', "Validation of the payment method"),
            ('offline', "Offline payment by token"),
            ('refund', "Refund"),
        ],
        readonly=True,
        index=True,
    )
    is_live = fields.Boolean(
        string="Production Environment",
        help="Whether the transaction happened in a production environment. False for transactions"
             " created before this tracking was implemented.",
    )
    source_transaction_id = fields.Many2one(
        string="Source Transaction",
        comodel_name='payment.transaction',
        index='btree_not_null',
        help="The source transaction of the related child transactions",
        readonly=True,
    )
    child_transaction_ids = fields.One2many(
        string="Child Transactions",
        help="The child transactions of the transaction.",
        comodel_name='payment.transaction',
        inverse_name='source_transaction_id',
        readonly=True,
    )
    refunds_count = fields.Integer(string="Refunds Count", compute='_compute_refunds_count')

    # Fields used for user redirection & payment post-processing
    is_post_processed = fields.Boolean(
        string="Is Post-processed", help="Has the payment been post-processed")
    tokenize = fields.Boolean(
        string="Create Token",
        help="Whether a payment token should be created when post-processing the transaction")
    landing_route = fields.Char(
        string="Landing Route",
        help="The route the user is redirected to after the transaction")

    # Duplicated partner values allowing to keep a record of them, should they be later updated.
    partner_id = fields.Many2one(
        string="Customer", comodel_name='res.partner', readonly=True, required=True,
        ondelete='restrict')
    partner_name = fields.Char(string="Partner Name")
    partner_lang = fields.Selection(string="Language", selection=_lang_get)
    partner_email = fields.Char(string="Email")
    partner_address = fields.Char(string="Address")
    partner_zip = fields.Char(string="Zip")
    partner_city = fields.Char(string="City")
    partner_state_id = fields.Many2one(string="State", comodel_name='res.country.state')
    partner_country_id = fields.Many2one(string="Country", comodel_name='res.country')
    partner_phone = fields.Char(string="Phone")

    _reference_uniq = models.Constraint(
        'unique(reference)',
        'Reference must be unique!',
    )

    # === COMPUTE METHODS === #

    def _compute_primary_payment_method_id(self):
        for pm, txs in self.grouped('payment_method_id').items():
            txs.primary_payment_method_id = pm.primary_payment_method_id or pm

    def _compute_refunds_count(self):
        rg_data = self.env['payment.transaction']._read_group(
            domain=[('source_transaction_id', 'in', self.ids), ('operation', '=', 'refund')],
            groupby=['source_transaction_id'],
            aggregates=['__count'],
        )
        data = {source_transaction.id: count for source_transaction, count in rg_data}
        for record in self:
            record.refunds_count = data.get(record.id, 0)

    # === CONSTRAINT METHODS === #

    @api.constrains('state')
    def _check_state_authorized_supported(self):
        """ Check that authorization is supported for a transaction in the `authorized` state. """
        illegal_authorize_state_txs = self.filtered(
            lambda tx: tx.state == 'authorized' and not tx.provider_id.support_manual_capture
        )
        if illegal_authorize_state_txs:
            raise ValidationError(_(
                "Transaction authorization is not supported by the following payment providers: %s",
                ', '.join(set(illegal_authorize_state_txs.mapped('provider_id.name')))
            ))

    @api.constrains('token_id')
    def _check_token_is_active(self):
        """ Check that the token used to create the transaction is active. """
        if self.token_id and not self.token_id.active:
            raise ValidationError(_("Creating a transaction from an archived token is forbidden."))

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            provider = self.env['payment.provider'].browse(values['provider_id'])

            if not values.get('reference'):
                values['reference'] = self._compute_reference(provider.code, **values)

            values['is_live'] = provider.state == 'enabled'

            # Duplicate partner values.
            partner = self.env['res.partner'].browse(values['partner_id'])
            partner_emails = email_normalize_all(partner.email)
            values.update({
                # Use the parent partner as fallback if the invoicing address has no name.
                'partner_name': partner.name or partner.parent_id.name,
                'partner_lang': partner.lang,
                'partner_email': partner_emails[0] if partner_emails else None,
                'partner_address': payment_utils.format_partner_address(
                    partner.street, partner.street2
                ),
                'partner_zip': partner.zip,
                'partner_city': partner.city,
                'partner_state_id': partner.state_id.id,
                'partner_country_id': partner.country_id.id,
                'partner_phone': partner.phone,
            })

            # Include provider-specific create values
            values.update(self._get_specific_create_values(provider.code, values))

        txs = super().create(vals_list)

        # Monetary fields are rounded with the currency at creation time by the ORM. Sometimes, this
        # can lead to inconsistent string representation of the amounts sent to the providers.
        # E.g., tx.create(amount=1111.11) -> tx.amount == 1111.1100000000001
        # To ensure a proper string representation, we invalidate this request's cache values of the
        # `amount` field for the created transactions. This forces the ORM to read the values from
        # the DB where there were stored using `float_repr`, which produces a result consistent with
        # the format expected by providers.
        # E.g., tx.create(amount=1111.11) ; tx.invalidate_recordset() -> tx.amount == 1111.11
        txs.invalidate_recordset(['amount'])

        return txs

    @api.model
    def _get_specific_create_values(self, provider_code, values):
        """ Complete the values of the `create` method with provider-specific values.

        For a provider to add its own create values, it must overwrite this method and return a dict
        of values. Provider-specific values take precedence over those of the dict of generic create
        values.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict values: The original create values.
        :return: The dict of provider-specific create values.
        :rtype: dict
        """
        return dict()

    # === ACTION METHODS === #

    def action_view_refunds(self):
        """ Return the windows action to browse the refund transactions linked to the transaction.

        Note: `self.ensure_one()`

        :return: The window action to browse the refund transactions.
        :rtype: dict
        """
        self.ensure_one()

        action = {
            'name': _("Refund"),
            'res_model': 'payment.transaction',
            'type': 'ir.actions.act_window',
        }
        if self.refunds_count == 1:
            refund_tx = self.env['payment.transaction'].search([
                ('source_transaction_id', '=', self.id),
            ])[0]
            action['res_id'] = refund_tx.id
            action['view_mode'] = 'form'
        else:
            action['view_mode'] = 'list,form'
            action['domain'] = [('source_transaction_id', '=', self.id)]
        return action

    def action_capture(self):
        """Open the partial capture wizard if it is supported by the related providers, otherwise
        capture the transactions immediately.

        :return: The action to open the partial capture wizard, if supported.
        :rtype: action.act_window|None
        """
        payment_utils.check_rights_on_recordset(self)

        if any(tx.provider_id.sudo().support_manual_capture == 'partial' for tx in self):
            return {
                'name': _("Capture"),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'payment.capture.wizard',
                'target': 'new',
                'context': {
                    'active_model': 'payment.transaction',
                    # Consider also confirmed transactions to calculate the total authorized amount.
                    'active_ids': self.filtered(lambda tx: tx.state in ['authorized', 'done']).ids,
                },
            }
        else:
            captured_txs_sudo = self.env['payment.transaction'].sudo()
            for tx in self.filtered(lambda tx: tx.state == 'authorized'):
                # In sudo mode to read on provider fields.
                captured_txs_sudo |= tx.sudo()._capture()
            return captured_txs_sudo._build_action_feedback_notification()

    def action_void(self):
        """Check the state of the transaction and request to have them voided."""
        payment_utils.check_rights_on_recordset(self)

        if any(tx.state != 'authorized' for tx in self):
            raise ValidationError(_("Only authorized transactions can be voided."))

        voided_txs_sudo = self.env['payment.transaction'].sudo()
        for tx in self:
            # Consider all the confirmed partial capture (same operation as parent) child txs.
            captured_amount = sum(child_tx.amount for child_tx in tx.child_transaction_ids.filtered(
                lambda t: t.state == 'done' and t.operation == tx.operation
            ))
            # In sudo mode to read on provider fields.
            voided_txs_sudo |= tx.sudo()._void(amount_to_void=tx.amount - captured_amount)
        return voided_txs_sudo._build_action_feedback_notification()

    def action_refund(self, amount_to_refund=None):
        """Check the state of the transactions and request their refund.

        :param float amount_to_refund: The amount to be refunded.
        :return: None
        """
        payment_utils.check_rights_on_recordset(self)

        if any(tx.state != 'done' for tx in self):
            raise ValidationError(_("Only confirmed transactions can be refunded."))

        refunded_txs_sudo = self.env['payment.transaction'].sudo()
        for tx in self:
            # In sudo mode to read on provider fields.
            refunded_txs_sudo |= tx.sudo()._refund(amount_to_refund=amount_to_refund)
        return refunded_txs_sudo._build_action_feedback_notification()

    def _build_action_feedback_notification(self):
        """Build a client notification to display the result of an action.

        :return: The client notification.
        :rtype: dict
        """
        if not (failed_txs := self.filtered(lambda tx: tx.state == 'error')):
            notification_type = 'success'
            msg = self.env._("Your payment operation has been successfully submitted.")
        else:
            notification_type = 'danger'
            msg = self.env._(
                "Your payment operation could not be completed for following transactions:"
                " %(tx_refs)s", tx_refs=', '.join(failed_txs.mapped('reference'))
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': notification_type,
                'message': msg,
                'next': {'type': 'ir.actions.act_window_close'},  # Close any open wizard.
            },
        }

    # === BUSINESS METHODS - PRE-PROCESSING === #

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """ Compute a unique reference for the transaction.

        The reference corresponds to the prefix if no other transaction with that prefix already
        exists. Otherwise, it follows the pattern `{computed_prefix}{separator}{sequence_number}`
        where:

        - `{computed_prefix}` is:

          - The provided custom prefix, if any.
          - The computation result of :meth:`_compute_reference_prefix` if the custom prefix is not
            filled, but the kwargs are.
          - `'tx-{datetime}'` if neither the custom prefix nor the kwargs are filled.

        - `{separator}` is the string that separates the prefix from the sequence number.
        - `{sequence_number}` is the next integer in the sequence of references sharing the same
          prefix. The sequence starts with `1` if there is only one matching reference.

        .. example::

           - Given the custom prefix `'example'` which has no match with an existing reference, the
             full reference will be `'example'`.
           - Given the custom prefix `'example'` which matches the existing reference `'example'`,
             and the custom separator `'-'`, the full reference will be `'example-1'`.
           - Given the kwargs `{'invoice_ids': [1, 2]}`, the custom separator `'-'` and no custom
             prefix, the full reference will be `'INV1-INV2'` (or similar) if no existing reference
             has the same prefix, or `'INV1-INV2-n'` if `n` existing references have the same
             prefix.

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :param str separator: The custom separator used to separate the prefix from the suffix.
        :param dict kwargs: Optional values passed to :meth:`_compute_reference_prefix` if no custom
                            prefix is provided.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        # Compute the prefix.
        if prefix:
            # Replace special characters by their ASCII alternative (é -> e ; ä -> a ; ...)
            prefix = unicodedata.normalize('NFKD', prefix).encode('ascii', 'ignore').decode('utf-8')
        if not prefix:  # Prefix not provided or voided above, compute it based on the kwargs.
            prefix = self.sudo()._compute_reference_prefix(separator, **kwargs)
        if not prefix:  # Prefix not computed from the kwargs, fallback on time-based value
            prefix = payment_utils.singularize_reference_prefix()

        # Compute the sequence number.
        reference = prefix  # The first reference of a sequence has no sequence number.
        if self.sudo().search_count([('reference', '=', prefix)], limit=1):  # The reference already has a match
            # We now execute a second search on `payment.transaction` to fetch all the references
            # starting with the given prefix. The load of these two searches is mitigated by the
            # index on `reference`. Although not ideal, this solution allows for quickly knowing
            # whether the sequence for a given prefix is already started or not, usually not. An SQL
            # query wouldn't help either as the selector is arbitrary and doing that would be an
            # open-door to SQL injections.
            same_prefix_references = self.sudo().search(
                [('reference', '=like', f'{prefix}{separator}%')]
            ).with_context(prefetch_fields=False).mapped('reference')

            # A final regex search is necessary to figure out the next sequence number. The previous
            # search could not rely on alphabetically sorting the reference to infer the largest
            # sequence number because both the prefix and the separator are arbitrary. A given
            # prefix could happen to be a substring of the reference from a different sequence.
            # For instance, the prefix 'example' is a valid match for the existing references
            # 'example', 'example-1' and 'example-ref', in that order. Trusting the order to infer
            # the sequence number would lead to a collision with 'example-1'.
            search_pattern = re.compile(rf'^{re.escape(prefix)}{separator}(\d+)$')
            max_sequence_number = 0  # If no match is found, start the sequence with this reference.
            for existing_reference in same_prefix_references:
                search_result = re.search(search_pattern, existing_reference)
                if search_result:  # The reference has the same prefix and is from the same sequence
                    # Find the largest sequence number, if any.
                    current_sequence = int(search_result.group(1))
                    if current_sequence > max_sequence_number:
                        max_sequence_number = current_sequence

            # Compute the full reference.
            reference = f'{prefix}{separator}{max_sequence_number + 1}'
        return reference

    @api.model
    def _compute_reference_prefix(self, separator, **values):
        """ Compute the reference prefix from the transaction values.

        Note: This method should be called in sudo mode to give access to the documents (invoices,
        sales orders) referenced in the transaction values.

        :param str separator: The custom separator used to separate parts of the computed
                              reference prefix.
        :param dict values: The transaction values used to compute the reference prefix.
        :return: The computed reference prefix.
        :rtype: str
        """
        return ''

    def _get_processing_values(self):
        """ Return the values used to process the transaction.

        The values are returned as a dict containing entries with the following keys:

        - `provider_id`: The provider handling the transaction, as a `payment.provider` id.
        - `provider_code`: The code of the provider.
        - `reference`: The reference of the transaction.
        - `amount`: The rounded amount of the transaction.
        - `currency_id`: The currency of the transaction, as a `res.currency` id.
        - `partner_id`: The partner making the transaction, as a `res.partner` id.
        - `should_tokenize`: Whether this transaction should be tokenized.
        - Additional provider-specific entries.

        Note: `self.ensure_one()`

        :return: The processing values.
        :rtype: dict
        """
        self.ensure_one()

        processing_values = {
            'provider_id': self.provider_id.id,
            'provider_code': self.provider_code,
            'reference': self.reference,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'should_tokenize': self.tokenize,
        }

        # Complete generic processing values with provider-specific values.
        processing_values.update(self._get_specific_processing_values(processing_values))

        # Render the HTML form for the redirect flow if available.
        if self.operation in ('online_redirect', 'validation'):
            redirect_form_view = self.provider_id._get_redirect_form_view(
                is_validation=self.operation == 'validation'
            )
            if redirect_form_view:  # Some providers don't need a redirect form.
                rendering_values = self._get_specific_rendering_values(processing_values)
                redirect_form_html = self.env['ir.qweb']._render(
                    redirect_form_view.id, rendering_values
                )
                processing_values.update(redirect_form_html=redirect_form_html)

        # Include the state and state message only after they might have been updated by calling the
        # `_get_specific_rendering/processing_values` methods (due to possible external requests).
        processing_values.update({
            'state': self.state,
            'state_message': self.state_message,
        })

        return processing_values

    def _get_specific_processing_values(self, processing_values):
        """ Return a dict of provider-specific values used to process the transaction.

        For a provider to add its own processing values, it must overwrite this method and return a
        dict of provider-specific values based on the generic values returned by this method.
        Provider-specific values take precedence over those of the dict of generic processing
        values.

        :param dict processing_values: The generic processing values of the transaction.
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        return dict()

    def _get_specific_rendering_values(self, processing_values):
        """ Return a dict of provider-specific values used to render the redirect form.

        For a provider to add its own rendering values, it must overwrite this method and return a
        dict of provider-specific values based on the processing values (provider-specific
        processing values included).

        :param dict processing_values: The processing values of the transaction.
        :return: The dict of provider-specific rendering values.
        :rtype: dict
        """
        return dict()

    def _get_mandate_values(self):
        """ Return a dict of module-specific values used to create a mandate.

        For a module to add its own mandate values, it must overwrite this method and return a dict
        of module-specific values.

        Note: `self.ensure_one()`

        :return: The dict of module-specific mandate values.
        :rtype: dict
        """
        self.ensure_one()
        return dict()

    def _charge_with_token(self):
        """Pay the transaction with the given token.

        Note: `self.ensure_one()`

        :return: None
        """
        self.ensure_one()
        self._ensure_provider_is_not_disabled()
        self._log_sent_message()
        try:
            self._send_payment_request()
        except ValidationError as e:
            self._set_error(str(e))

    def _send_payment_request(self):
        """Request the provider handling the transaction to send a token payment request.

        This method is exclusively used to make payments by token, which correspond to both the
        `online_token` and the `offline` transaction's `operation` field.

        For a provider to support tokenization, it must override this method and send an API request
        to make a payment.

        Note: `self.ensure_one()` from :meth:`_charge_with_token`

        :return: None
        """
        return

    def _capture(self, amount_to_capture=None):
        """Capture the authorized amount.

        Note: `self.ensure_one()`

        :param float amount_to_capture: The amount to capture.
        :return: The capture transaction created to process the capture request.
        :rtype: payment.transaction
        """
        self.ensure_one()
        self._ensure_provider_is_not_disabled()

        capture_tx = self._create_child_transaction(amount_to_capture or self.amount)
        capture_tx._log_sent_message()
        try:
            capture_tx._send_capture_request()
        except ValidationError as e:
            capture_tx._set_error(str(e))
        return capture_tx

    def _send_capture_request(self):
        """Request the provider handling the transaction to send a capture request.

        For a provider to support authorization, it must override this method and send an API
        request to capture the payment.

        Note: `self.ensure_one()` from :meth:`_capture`

        :return: None
        """
        return

    def _void(self, amount_to_void=None):
        """Void the authorized amount.

        Note: `self.ensure_one()`

        :param float amount_to_void: The amount to be voided.
        :return: The void transaction created to process the void request.
        :rtype: payment.transaction
        """
        self.ensure_one()
        self._ensure_provider_is_not_disabled()

        void_tx = self._create_child_transaction(amount_to_void or self.amount)
        void_tx._log_sent_message()
        try:
            void_tx._send_void_request()
        except ValidationError as e:
            void_tx._set_error(str(e))
        return void_tx

    def _send_void_request(self):
        """Request the provider handling the transaction to send a void request.

        For a provider to support authorization, it must override this method and send an API
        request to void the payment.

        Note: `self.ensure_one()` from :meth:`_void`

        :return: None
        """
        return

    def _refund(self, amount_to_refund=None):
        """Refund the transaction.

        Note: `self.ensure_one()`

        :param float amount_to_refund: The amount to be refunded.
        :return: The refund transaction created to process the refund request.
        :rtype: payment.transaction
        """
        self.ensure_one()
        self._ensure_provider_is_not_disabled()

        refund_tx = self._create_child_transaction(amount_to_refund or self.amount, is_refund=True)
        refund_tx._log_sent_message()
        try:
            refund_tx._send_refund_request()
        except ValidationError as e:
            refund_tx._set_error(str(e))
        return refund_tx

    def _send_refund_request(self):
        """Request the provider handling the transaction to send a refund request.

        For a provider to support refunds, it must override this method and send an API request to
        make a refund.

        Note: `self.ensure_one()` from :meth:`_refund`

        :return: None
        """
        return

    def _ensure_provider_is_not_disabled(self):
        """ Ensure that the provider's state is not `disabled` before sending a request to its
        provider.

        :return: None
        :raise UserError: If the provider's state is `disabled`.
        """
        if self.provider_id.state == 'disabled':
            raise UserError(_(
                "Making a request to the provider is not possible because the provider is disabled."
            ))

    def _create_child_transaction(self, amount, is_refund=False, **custom_create_values):
        """ Create a new transaction with the current transaction as its parent transaction.

        This happens only in case of a refund or a partial capture (where the initial transaction is
        split between smaller transactions, either captured or voided).

        Note: self.ensure_one()

        :param float amount: The strictly positive amount of the child transaction, in the same
                             currency as the source transaction.
        :param bool is_refund: Whether the child transaction is a refund.
        :return: The created child transaction.
        :rtype: payment.transaction
        """
        self.ensure_one()

        if is_refund:
            reference_prefix = f'R-{self.reference}'
            amount = -amount
            operation = 'refund'
        else:  # Partial capture or void.
            reference_prefix = f'P-{self.reference}'
            operation = self.operation

        return self.create({
            'provider_id': self.provider_id.id,
            'payment_method_id': self.payment_method_id.id,
            'reference': self._compute_reference(self.provider_code, prefix=reference_prefix),
            'amount': amount,
            'currency_id': self.currency_id.id,
            'token_id': self.token_id.id,
            'operation': operation,
            'source_transaction_id': self.id,
            'partner_id': self.partner_id.id,
            **custom_create_values,
        })

    # === BUSINESS METHODS - PROCESSING === #

    def _process(self, provider_code, payment_data):
        """Process the payment data received from the provider and update the transaction.

        :param str provider_code: The code of the provider handling the transaction.
        :param dict payment_data: The payment data sent by the provider.
        :return: The updated transaction.
        :rtype: payment.transaction
        """
        tx = self or self._search_by_reference(provider_code, payment_data)
        if tx:
            tx.ensure_one()
            tx._validate_amount(payment_data)
            tx._apply_updates(payment_data)
            if tx.tokenize and tx.state in {'authorized', 'done'}:
                tx._tokenize(payment_data)
        return tx

    @api.model
    def _search_by_reference(self, provider_code, payment_data):
        """Search the transaction based on the payment data.

        :param str provider_code: The code of the provider handling the transaction.
        :param dict payment_data: The payment data sent by the provider.
        :return: The transaction, if found.
        :rtype: payment.transaction
        """
        reference = self._extract_reference(provider_code, payment_data)
        if not reference:
            _logger.warning(
                "Received payment data from provider %s with missing reference", provider_code
            )
            return self

        tx = self.search(
            Domain('reference', '=', reference) & Domain('provider_code', '=', provider_code)
        )
        if not tx:
            _logger.warning("No transaction found matching reference %s.", reference)
        return tx

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Extract the transaction reference from the payment data.

        This method must be overridden by providers to extract the reference from the payment data.

        :param str provider_code: The code of the provider handling the transaction.
        :param dict payment_data: The payment data sent by the provider.
        :return: The transaction reference.
        :rtype: str
        """
        return payment_data.get('reference')

    def _validate_amount(self, payment_data):
        """Ensure that the transaction's amount and currency match the ones from the payment data.

        :param dict payment_data: The payment data sent by the provider.
        :return: None
        :raise ValidationError: If the transaction's amount and currency don't match the ones from
                                the payment data.
        """
        self.ensure_one()

        amount_data = self._extract_amount_data(payment_data)
        if amount_data is None:
            return  # Skip the amount validation.

        amount = amount_data['amount']
        currency_code = amount_data['currency_code']
        precision_digits = amount_data.get('precision_digits')

        if not amount or not currency_code:
            error_message = _("The amount or currency is missing from the payment data.")
            self._set_error(error_message)
            raise ValidationError(error_message)

        # Negate the amount for refunds, as refunds have a negative amount in Odoo, but all
        # providers send a positive one.
        if self.operation == 'refund':
            amount = -amount
        tx_amount = self.amount if precision_digits is None else float_round(
            self.amount, precision_digits=precision_digits, rounding_method='DOWN'
        )
        if self.currency_id.compare_amounts(amount, tx_amount) != 0:
            error_message = _(
                "The amount from the payment data doesn't match the one from the transaction."
            )
            self._set_error(error_message)
            raise ValidationError(error_message)

        if currency_code != self.currency_id.name:
            error_message = _(
                "The currency from the payment data doesn't match the one from the transaction."
            )
            self._set_error(error_message)
            raise ValidationError(error_message)

    def _extract_amount_data(self, payment_data):
        """Extract the amount, currency and rounding precision from the payment data.

        This method must be overridden by providers to parse the amount data from the payment data.
        If the provider returns `None`, the amount validation is skipped.

        :param dict payment_data: The payment data sent by the provider.
        :return: The amount data, in the {amount: float, currency_code: str, precision_digits: int}
                 format.
        :rtype: dict|None
        """
        return {}

    def _apply_updates(self, payment_data):
        """Update the transaction based on the payment data received from the provider.

        The updates typically include the payment's state, the provider reference, and the selected
        payment method.

        This method should not be called directly; payment data should go through :meth:`_process`.

        This method must be overridden by providers to update the transaction based on the payment
        data.

        Note: `self.ensure_one()` from :meth:`_process`

        :param dict payment_data: The payment data sent by the provider.
        :return: None
        """
        return

    def _tokenize(self, payment_data):
        """Create a new token based on the payment data.

        :param dict payment_data: The payment data sent by the provider.
        :return: None
        """
        self.ensure_one()

        if not (token_values := self._extract_token_values(payment_data)):
            return

        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_method_id': self.payment_method_id.id,
            'partner_id': self.partner_id.id,
            **token_values,
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })
        _logger.info(
            "Token %(token_id)s created for partner %(partner_id)s from transaction %(ref)s.",
            {'token_id': token.id, 'partner_id': self.partner_id.id, 'ref': self.reference},
        )

    def _extract_token_values(self, payment_data):
        """Extract the create values of a token from the payment data.

        Providers can override this to supply their own token data based on the payment data.

        Note: self.ensure_one() from :meth: `_tokenize`

        :param dict payment_data: Data sent by the provider.
        :return: Data to create a payment token.
        :rtype: dict
        """
        return dict()

    def _set_pending(self, *, state_message=None, extra_allowed_states=()):
        """ Update the transactions' state to `pending`.

        :param str state_message: The reason for setting the transactions in the state `pending`.
        :param tuple[str] extra_allowed_states: The extra states that should be considered allowed
                                                target states for the source state 'pending'.
        :return: The updated transactions.
        :rtype: recordset of `payment.transaction`
        """
        allowed_states = ('draft',)
        target_state = 'pending'
        txs_to_process = self._update_state(
            allowed_states + extra_allowed_states, target_state, state_message
        )
        txs_to_process._log_received_message()
        return txs_to_process

    def _set_authorized(self, *, state_message=None, extra_allowed_states=()):
        """ Update the transactions' state to `authorized`.

        :param str state_message: The reason for setting the transactions in the state `authorized`.
        :param tuple[str] extra_allowed_states: The extra states that should be considered allowed
                                                target states for the source state 'authorized'.
        :return: The updated transactions.
        :rtype: recordset of `payment.transaction`
        """
        allowed_states = ('draft', 'pending')
        target_state = 'authorized'
        txs_to_process = self._update_state(
            allowed_states + extra_allowed_states, target_state, state_message
        )
        txs_to_process._log_received_message()
        return txs_to_process

    def _set_done(self, *, state_message=None, extra_allowed_states=()):
        """ Update the transactions' state to `done`.

        :param str state_message: The reason for setting the transactions in the state `done`.
        :param tuple[str] extra_allowed_states: The extra states that should be considered allowed
                                                target states for the source state 'done'.
        :return: The updated transactions.
        :rtype: recordset of `payment.transaction`
        """
        allowed_states = ('draft', 'pending', 'authorized', 'error')
        target_state = 'done'
        txs_to_process = self._update_state(
            allowed_states + extra_allowed_states, target_state, state_message
        )
        txs_to_process._log_received_message()
        txs_to_process._update_source_transaction_state()
        return txs_to_process

    def _set_canceled(self, state_message=None, extra_allowed_states=()):
        """ Update the transactions' state to `cancel`.

        :param str state_message: The reason for setting the transactions in the state `cancel`.
        :param tuple[str] extra_allowed_states: The extra states that should be considered allowed
                                                target states for the source state 'canceled'.
        :return: The updated transactions.
        :rtype: recordset of `payment.transaction`
        """
        allowed_states = ('draft', 'pending', 'authorized')
        target_state = 'cancel'
        txs_to_process = self._update_state(
            allowed_states + extra_allowed_states, target_state, state_message
        )
        txs_to_process._log_received_message()
        txs_to_process._update_source_transaction_state()
        return txs_to_process

    def _set_error(self, state_message, extra_allowed_states=()):
        """ Update the transactions' state to `error`.

        :param str state_message: The reason for setting the transactions in the state `error`.
        :param tuple[str] extra_allowed_states: The extra states that should be considered allowed
                                                target states for the source state 'error'.
        :return: The updated transactions.
        :rtype: recordset of `payment.transaction`
        """
        allowed_states = ('draft', 'pending', 'authorized')
        target_state = 'error'
        txs_to_process = self._update_state(
            allowed_states + extra_allowed_states, target_state, state_message
        )
        txs_to_process._log_received_message()
        return txs_to_process

    def _update_state(self, allowed_states, target_state, state_message):
        """ Update the transactions' state to the target state if the current state allows it.

        If the current state is the same as the target state, the transaction is skipped and a log
        with level INFO is created.

        :param tuple[str] allowed_states: The allowed source states for the target state.
        :param str target_state: The target state.
        :param str state_message: The message to set as `state_message`.
        :return: The recordset of transactions whose state was updated.
        :rtype: recordset of `payment.transaction`
        """
        def classify_by_state(transactions_):
            """ Classify the transactions according to their current state.

            For each transaction of the current recordset, if:

            - The state is an allowed state: the transaction is flagged as `to process`.
            - The state is equal to the target state: the transaction is flagged as `processed`.
            - The state matches none of above: the transaction is flagged as `in wrong state`.

            :param recordset transactions_: The transactions to classify, as a `payment.transaction`
                                            recordset.
            :return: A 3-items tuple of recordsets of classified transactions, in this order:
                     transactions `to process`, `processed`, and `in wrong state`.
            :rtype: tuple(recordset)
            """
            txs_to_process_ = transactions_.filtered(lambda _tx: _tx.state in allowed_states)
            txs_already_processed_ = transactions_.filtered(lambda _tx: _tx.state == target_state)
            txs_wrong_state_ = transactions_ - txs_to_process_ - txs_already_processed_

            return txs_to_process_, txs_already_processed_, txs_wrong_state_

        txs_to_process, txs_already_processed, txs_wrong_state = classify_by_state(self)
        for tx in txs_already_processed:
            _logger.info(
                "Skipped the update of transaction %(ref)s as it is already in state %(state)s.",
                {'ref': tx.reference, 'state': tx.state},
            )
        for tx in txs_wrong_state:
            _logger.warning(
                "Refused to update transaction %(ref)s from state %(tx_state)s to state"
                " %(target_state)s; allowed source states are: %(allowed_states)s.",
                {
                    'ref': tx.reference,
                    'tx_state': tx.state,
                    'target_state': target_state,
                    'allowed_states': allowed_states,
                },
            )
        txs_to_process.write({
            'state': target_state,
            'state_message': state_message,
            'last_state_change': fields.Datetime.now(),
            'is_post_processed': False,  # Reset to allow post-processing again for other states.
        })
        return txs_to_process

    def _update_source_transaction_state(self):
        """ Update the state of the source transactions for which all child transactions have
        reached a final state.

        :return: None
        """
        for child_tx in self.filtered('source_transaction_id'):
            sibling_txs = child_tx.source_transaction_id.child_transaction_ids.filtered(
                lambda tx: tx.state in ['done', 'cancel'] and tx.operation == child_tx.operation
            )
            processed_amount = round(
                sum(tx.amount for tx in sibling_txs), child_tx.currency_id.decimal_places
            )
            if child_tx.source_transaction_id.amount == processed_amount:
                fully_voided = all(tx.state == 'cancel' for tx in sibling_txs)
                target_state = 'cancel' if fully_voided else 'done'
                # Call `_update_state` directly instead of `_set_authorized` to avoid looping.
                child_tx.source_transaction_id._update_state(('authorized',), target_state, '')
                child_tx.source_transaction_id._log_received_message()

    # === BUSINESS METHODS - POST-PROCESSING === #

    def _cron_post_process(self):
        """ Trigger the post-processing of the transactions that were not handled by the client in
        the `poll_status` controller method.

        :return: None
        """
        txs_to_post_process = self
        if not txs_to_post_process:
            # Don't try forever to post-process a transaction that doesn't go through. Set the limit
            # to 4 days because some providers (PayPal) need that much for the payment verification.
            retry_limit_date = datetime.now() - relativedelta.relativedelta(days=4)
            # Retrieve all transactions matching the criteria for post-processing
            txs_to_post_process = self.search(
                [('is_post_processed', '=', False), ('last_state_change', '>=', retry_limit_date)]
            )
        for tx in txs_to_post_process:
            try:
                tx._post_process()
                self.env.cr.commit()
            except psycopg2.OperationalError:
                self.env.cr.rollback()  # Rollback and try later.
            except Exception as e:
                _logger.exception(
                    "An error occurred while post-processing transaction %s:\n%s",
                    tx.reference, e
                )
                self.env.cr.rollback()

    def _post_process(self):
        """ Post-process the transactions.

        The generic post-processing only consists in flagging the transactions as post-processed.
        For a module to add its own logic to the post-processing, it must overwrite this method and
        apply its specific logic to the transactions, optionally after filtering them based on their
        state.

        :return: None
        """
        self.is_post_processed = True

    # === REQUEST HELPERS === #

    def _send_api_request(self, method, endpoint, *, params=None, data=None, json=None, **kwargs):
        """Send a request to the API.

        This method serves as a helper to:

        1. Pass the transaction reference to the provider's
           :meth:`~odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request`
           method.
        2. Set the transaction's state to `error` if the request fails, with the exception's message
           as the `state_message`.

        Note: `self.ensure_one()`

        :param str method: The HTTP method of the request.
        :param str endpoint: The endpoint of the API to reach with the request.
        :param dict params: The query string parameters of the request.
        :param dict|str data: The body of the request.
        :param dict json: The JSON-formatted body of the request.
        :param dict kwargs: Provider-specific data forwarded to the specialized helper methods.
        :return: The formatted content of the response.
        :rtype: dict|str
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()
        return self.provider_id._send_api_request(
            method,
            endpoint,
            params=params,
            data=data,
            json=json,
            reference=self.reference,
            **kwargs,
        )

    # === LOGGING HELPERS === #

    def _log_sent_message(self):
        """Log that the transactions have been created in the chatter of relevant documents.

        :return: None
        """
        for tx in self:
            if message := tx._get_sent_message():
                tx._log_message_on_linked_documents(message)

    def _log_received_message(self):
        """Log that the transactions have been processed in the chatter of relevant documents.

        :return: None
        """
        for tx in self:
            if message := tx._get_received_message():
                tx._log_message_on_linked_documents(message)

    def _log_message_on_linked_documents(self, message):
        """ Log a message on the records linked to the transaction.

        For a module to implement payments and link documents to a transaction, it must override
        this method and call it, then log the message on documents linked to the transaction.

        Note: `self.ensure_one()`

        :param str message: The message to log.
        :return: None
        """
        self.ensure_one()

    # === GETTERS === #

    def _get_sent_message(self):
        """Return the message to log to state that the transaction has been created.

        Note: `self.ensure_one()`

        :return: The message to log.
        :rtype: str
        """
        self.ensure_one()

        # Choose the message based on the payment flow.
        if self.operation in {'online_redirect', 'online_direct', 'online_token', 'offline'}:
            sent_message = _(
                "The transaction %(ref)s of %(formatted_amount)s has been initiated.",
                ref=self._get_html_link(), formatted_amount=self.currency_id.format(self.amount)
            )
        elif self.operation == 'refund':
            sent_message = _(
                "The refund %(ref)s of %(formatted_amount)s has been initiated.",
                ref=self._get_html_link(), formatted_amount=self.currency_id.format(-self.amount)
            )
        else:  # 'validation'
            sent_message = None  # No message to log for initiating validation transactions.
        return sent_message

    def _get_received_message(self):
        """Return the message to log to state that the transaction has been processed.

        Note: `self.ensure_one()`

        :return: The message to log.
        :rtype: str
        """
        self.ensure_one()

        if self.operation == 'validation':
            return None  # Don't log anything as the token is not yet created.

        # Choose the message based on the transaction's state.
        msg_values = {
            'tx_label': 'refund' if self.operation == 'refund' else 'transaction',
            'ref': self._get_html_link(),
            'formatted_amount': self.currency_id.format(self.amount),
        }
        match self.state:
            case 'pending':
                received_message = _(
                    "The %(tx_label)s %(ref)s of %(formatted_amount)s is pending.",
                    **msg_values,
                )
            case 'authorized':
                received_message = _(
                    "The %(tx_label)s %(ref)s of %(formatted_amount)s has been authorized.",
                    **msg_values,
                )
            case 'done':
                received_message = _(
                    "The %(tx_label)s %(ref)s of %(formatted_amount)s has been confirmed.",
                    **msg_values,
                )
            case 'cancel':
                received_message = _(
                    "The %(tx_label)s %(ref)s of %(formatted_amount)s has been canceled.",
                    **msg_values,
                )
            case 'error':
                received_message = _(
                    "The %(tx_label)s %(ref)s of %(formatted_amount)s encountered an error.",
                    **msg_values,
                )
            case _:
                received_message = None

        # Append any state_message for cancel or error.
        if self.state in {'cancel', 'error'} and self.state_message:
            received_message += Markup("<br/>") + self.state_message

        return received_message

    def _get_last(self):
        """ Return the last transaction of the recordset.

        :return: The last transaction of the recordset, sorted by id.
        :rtype: recordset of `payment.transaction`
        """
        return self.filtered(lambda t: t.state != 'draft').sorted()[:1]
