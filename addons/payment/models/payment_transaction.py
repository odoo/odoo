# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import logging
import pprint
import re
import unicodedata
from datetime import datetime

import psycopg2
from dateutil import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import consteq, ustr
from odoo.tools.misc import formatLang

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _name = 'payment.transaction'
    _description = 'Payment Transaction'
    _order = 'id desc'
    _rec_name = 'reference'

    @api.model
    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    acquirer_id = fields.Many2one(
        string="Acquirer", comodel_name='payment.acquirer', readonly=True, required=True)
    provider = fields.Selection(related='acquirer_id.provider')
    reference = fields.Char(
        string="Reference", help="The internal reference of the transaction", readonly=True,
        required=True, index=True)
    acquirer_reference = fields.Char(
        string="Acquirer Reference", help="The acquirer reference of the transaction",
        readonly=True)  # This is not the same thing as the acquirer reference of the token
    amount = fields.Monetary(
        string="Amount", currency_field='currency_id', readonly=True, required=True)
    currency_id = fields.Many2one(
        string="Currency", comodel_name='res.currency', readonly=True, required=True)
    fees = fields.Monetary(
        string="Fees", currency_field='currency_id',
        help="The fees amount; set by the system as it depends on the acquirer", readonly=True)
    token_id = fields.Many2one(
        string="Payment Token", comodel_name='payment.token', readonly=True,
        domain='[("acquirer_id", "=", "acquirer_id")]')
    state = fields.Selection(
        string="Status",
        selection=[('draft', "Draft"), ('pending', "Pending"), ('authorized', "Authorized"),
                   ('done', "Confirmed"), ('cancel', "Canceled"), ('error', "Error")],
        default='draft', readonly=True, required=True, copy=False)
    state_message = fields.Text(
        string="Message", help="The complementary information message about the state",
        readonly=True)
    last_state_change = fields.Datetime(
        string="Last State Change Date", readonly=True, default=fields.Datetime.now)

    # Fields used for traceability
    operation = fields.Selection(  # This should not be trusted if the state is 'draft' or 'pending'
        string="Operation",
        selection=[('online_redirect', "Online payment with redirection"),
                   ('online_direct', "Online direct payment"),
                   ('online_token', "Online payment by token"),
                   ('validation', "Validation of the payment method"),
                   ('offline', "Offline payment by token")],
        readonly=True)
    payment_id = fields.Many2one(string="Payment", comodel_name='account.payment', readonly=True)
    invoice_ids = fields.Many2many(
        string="Invoices", comodel_name='account.move', relation='account_invoice_transaction_rel',
        column1='transaction_id', column2='invoice_id', readonly=True, copy=False,
        domain=[('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'))])
    invoice_ids_nbr = fields.Integer(string="Invoices count", compute='_compute_invoice_ids_nbr')

    # Fields used for user redirection & payment post-processing
    is_post_processed = fields.Boolean(
        string="Is Post-processed", help="Has the payment been post-processed", default=False)
    tokenize = fields.Boolean(
        string="Create Token",
        help="Whether a payment token should be created when post-processing the transaction")
    validation_route = fields.Char(
        string="Validation Route",
        help="The route the user is redirected to in order to refund a validation transaction")
    landing_route = fields.Char(
        string="Landing Route",
        help="The route the user is redirected to after the transaction")
    callback_model_id = fields.Many2one(
        string="Callback Document Model", comodel_name='ir.model', groups='base.group_system')
    callback_res_id = fields.Integer(string="Callback Record ID", groups='base.group_system')
    callback_method = fields.Char(string="Callback Method", groups='base.group_system')
    # Hash for additional security on top of the callback fields' group in case a bug exposes a sudo
    callback_hash = fields.Char(string="Callback Hash", groups='base.group_system')
    callback_is_done = fields.Char(
        string="Callback Done", help="Whether the callback has already been executed",
        groups="base.group_system", readonly=True)

    # Duplicated partner values allowing to keep a record of them, should they be later updated
    partner_id = fields.Many2one(string="Customer", comodel_name='res.partner', readonly=True)
    partner_name = fields.Char(string="Partner Name")
    partner_lang = fields.Selection(string="Language", selection=_lang_get)
    partner_email = fields.Char(string="Email")
    partner_address = fields.Char(string="Address")
    partner_zip = fields.Char(string="Zip")
    partner_city = fields.Char(string="City")
    partner_state_id = fields.Many2one(string="State", comodel_name='res.country.state')
    partner_country_id = fields.Many2one(string="Country", comodel_name='res.country')
    partner_phone = fields.Char(string="Phone")

    _sql_constraints = [
        ('reference_uniq', 'unique(reference)', "Reference must be unique!"),
    ]

    #=== COMPUTE METHODS ===#

    @api.depends('invoice_ids')
    def _compute_invoice_ids_nbr(self):
        self.env.cr.execute(
            '''
            SELECT transaction_id, count(invoice_id)
            FROM account_invoice_transaction_rel
            WHERE transaction_id IN %s
            GROUP BY transaction_id
            ''',
            [tuple(self.ids)]
        )
        query_res = self.env.cr.fetchall()
        tx_data = {tx_id: invoice_count for tx_id, invoice_count in query_res}
        for tx in self:
            tx.invoice_ids_nbr = tx_data.get(tx.id, 0)

    #=== CONSTRAINS & ONCHANGE METHODS ===#

    @api.constrains('state')
    def _check_state_authorized_supported(self):
        """ Check that authorization is supported for a transaction in the 'authorized' state. """
        illegal_authorize_state_tx = self.filtered(
            lambda tx: tx.state == 'authorized' and not tx.acquirer_id.support_authorization
        )
        if illegal_authorize_state_tx:
            raise ValidationError(_(
                "Transaction authorization is not supported by the following payment acquirers: %s",
                ', '.join(set(illegal_authorize_state_tx.mapped('acquirer_id.name')))
            ))

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])

            if not values.get('reference'):
                values['reference'] = self._compute_reference(acquirer.provider, **values)

            # Compute fees
            values['fees'] = acquirer._compute_fees(
                values.get('amount'), values.get('currency_id'), values.get('partner_country_id')
            )

            # Duplicate partner values
            partner = self.env['res.partner'].browse(values['partner_id'])
            values.update({
                'partner_name': partner.name,
                'partner_lang': partner.lang,
                'partner_email': partner.email,
                'partner_address': payment_utils.format_partner_address(
                    partner.street, partner.street2
                ),
                'partner_zip': partner.zip,
                'partner_city': partner.city,
                'partner_state_id': partner.state_id.id,
                'partner_country_id': partner.country_id.id,
                'partner_phone': partner.phone,
            })

            # Include acquirer-specific create values
            values.update(self._get_specific_create_values(acquirer.provider, values))

            # Generate the hash for the callback if one has be configured on the tx
            values['callback_hash'] = self._generate_callback_hash(
                values.get('callback_model_id'),
                values.get('callback_res_id'),
                values.get('callback_method'),
            )

        return super().create(values_list)

    @api.model
    def _get_specific_create_values(self, provider, values):
        """ Complete the values of the `create` method with acquirer-specific values.

        For an acquirer to add its own create values, it must overwrite this method and return a
        dict of values. Acquirer-specific values take precedence over those of the dict of generic
        create values.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict values: The original create values
        :return: The dict of acquirer-specific create values
        :rtype: dict
        """
        return dict()

    #=== ACTION METHODS ===#

    def action_view_invoices(self):
        """ Return the action for the views of the invoices linked to the transaction.

        Note: self.ensure_one()

        :return: The action
        :rtype: dict
        """
        self.ensure_one()

        action = {
            'name': _("Invoices"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'target': 'current',
        }
        invoice_ids = self.invoice_ids.ids
        if len(invoice_ids) == 1:
            invoice = invoice_ids[0]
            action['res_id'] = invoice
            action['view_mode'] = 'form'
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('id', 'in', invoice_ids)]
        return action

    def action_capture(self):
        """ Check the state of the transactions and request their capture. """
        if any(tx.state != 'authorized' for tx in self):
            raise ValidationError(_("Only authorized transactions can be captured."))

        for tx in self:
            tx._send_capture_request()

    def action_void(self):
        """ Check the state of the transaction and request to have them voided. """
        if any(tx.state != 'authorized' for tx in self):
            raise ValidationError(_("Only authorized transactions can be voided."))

        for tx in self:
            tx._send_void_request()

    #=== BUSINESS METHODS - PAYMENT FLOW ===#

    @api.model
    def _compute_reference(self, provider, prefix=None, separator='-', **kwargs):
        """ Compute a unique reference for the transaction.

        The reference either corresponds to the prefix if no other transaction with that prefix
        already exists, or follows the pattern `{computed_prefix}{separator}{sequence_number}` where
          - {computed_prefix} is:
            - The provided custom prefix, if any.
            - The computation result of `_compute_reference_prefix` if the custom prefix is not
              filled but the kwargs are.
            - 'tx-{datetime}', if neither the custom prefix nor the kwargs are filled.
          - {separator} is a custom string also used in `_compute_reference_prefix`.
          - {sequence_number} is the next integer in the sequence of references sharing the exact
            same prefix, '1' if there is only one matching reference (hence without sequence number)

        Examples:
          - Given the custom prefix 'example' which has no match with an existing reference, the
            full reference will be 'example'.
          - Given the custom prefix 'example' which matches the existing reference 'example', and
            the custom separator '-', the full reference will be 'example-1'.
          - Given the kwargs {'invoice_ids': [1, 2]}, the custom separator '-' and no custom prefix,
            the full reference will be 'INV1-INV2' (or similar) if no existing reference has the
            same prefix, or 'INV1-INV2-n' if n existing references have the same prefix.

        :param str provider: The provider of the acquirer handling the transaction
        :param str prefix: The custom prefix used to compute the full reference
        :param str separator: The custom separator used to separate the prefix from the suffix, and
                              passed to `_compute_reference_prefix` if it is called
        :param dict kwargs: Optional values passed as is to `_compute_reference_prefix` if no custom
                            prefix is provided
        :return: The unique reference for the transaction
        :rtype: str
        """
        # Compute the prefix
        if prefix:
            # Replace special characters by their ASCII alternative (é -> e ; ä -> a ; ...)
            prefix = unicodedata.normalize('NFKD', prefix).encode('ascii', 'ignore').decode('utf-8')
        if not prefix:  # Prefix not provided or voided above, compute it based on the kwargs
            prefix = self._compute_reference_prefix(provider, separator, **kwargs)
        if not prefix:  # Prefix not computed from the kwargs, fallback on time-based value
            prefix = payment_utils.singularize_reference_prefix()

        # Compute the sequence number
        reference = prefix  # The first reference of a sequence has no sequence number
        if self.sudo().search([('reference', '=', prefix)]):  # The reference already has a match
            # We now execute a second search on `payment.transaction` to fetch all the references
            # starting with the given prefix. The load of these two searches is mitigated by the
            # index on `reference`. Although not ideal, this solution allows for quickly knowing
            # whether the sequence for a given prefix is already started or not, usually not. An SQL
            # query wouldn't help either as the selector is arbitrary and doing that would be an
            # open-door to SQL injections.
            same_prefix_references = self.sudo().search(
                [('reference', 'like', f'{prefix}{separator}%')]
            ).with_context(prefetch_fields=False).mapped('reference')

            # A final regex search is necessary to figure out the next sequence number. The previous
            # search could not rely on alphabetically sorting the reference to infer the largest
            # sequence number because both the prefix and the separator are arbitrary. A given
            # prefix could happen to be a substring of the reference from a different sequence.
            # For instance, the prefix 'example' is a valid match for the existing references
            # 'example', 'example-1' and 'example-ref', in that order. Trusting the order to infer
            # the sequence number would lead to a collision with 'example-1'.
            search_pattern = re.compile(rf'^{prefix}{separator}(\d+)$')
            max_sequence_number = 0  # If no match is found, start the sequence with this reference
            for existing_reference in same_prefix_references:
                search_result = re.search(search_pattern, existing_reference)
                if search_result:  # The reference has the same prefix and is from the same sequence
                    # Find the largest sequence number, if any
                    current_sequence = int(search_result.group(1))
                    if current_sequence > max_sequence_number:
                        max_sequence_number = current_sequence

            # Compute the full reference
            reference = f'{prefix}{separator}{max_sequence_number + 1}'
        return reference

    @api.model
    def _compute_reference_prefix(self, provider, separator, **values):
        """ Compute the reference prefix from the transaction values.

        If the `values` parameter has an entry with 'invoice_ids' as key and a list of (4, id, O) or
        (6, 0, ids) X2M command as value, the prefix is computed based on the invoice name(s).
        Otherwise, an empty string is returned.

        :param str provider: The provider of the acquirer handling the transaction
        :param str separator: The custom separator used to separate data references
        :param dict values: The transaction values used to compute the reference prefix. It should
                            have the structure {'invoice_ids': [(X2M command), ...], ...}.
        :return: The computed reference prefix if invoice ids are found, an empty string otherwise
        :rtype: str
        """
        command_list = values.get('invoice_ids')
        if command_list:
            # Extract invoice id(s) from the X2M commands
            invoice_ids = self._fields['invoice_ids'].convert_to_cache(command_list, self)
            invoices = self.env['account.move'].browse(invoice_ids).exists()
            if len(invoices) == len(invoice_ids):  # All ids are valid
                return separator.join(invoices.mapped('name'))
        return ''

    @api.model
    def _generate_callback_hash(self, callback_model_id, callback_res_id, callback_method):
        """ Return the hash for the callback on the transaction.

        :param int callback_model_id: The model on which the callback method is defined, as a
                                      `res.model` id
        :param int callback_res_id: The record on which the callback method must be called, as an id
                                    of the callback model
        :param str callback_method: The name of the callback method
        :return: The callback hash
        :retype: str
        """
        if callback_model_id and callback_res_id and callback_method:
            secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
            model_name = self.env['ir.model'].sudo().browse(callback_model_id).model
            token = f'{model_name}{callback_res_id}{callback_method}'
            callback_hash = hmac.new(
                secret.encode('utf-8'), token.encode('utf-8'), hashlib.sha256
            ).hexdigest()
            return callback_hash
        return None

    def _get_processing_values(self):
        """ Return a dict of values used to process the transaction.

        The returned dict contains the following entries:
            - tx_id: The transaction, as a `payment.transaction` id
            - acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
            - provider: The provider of the acquirer
            - reference: The reference of the transaction
            - amount: The rounded amount of the transaction
            - currency_id: The currency of the transaction, as a res.currency id
            - partner_id: The partner making the transaction, as a res.partner id
            - Additional acquirer-specific entries

        Note: self.ensure_one()

        :return: The dict of processing values
        :rtype: dict
        """
        self.ensure_one()

        processing_values = {
            'acquirer_id': self.acquirer_id.id,
            'provider': self.provider,
            'reference': self.reference,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
        }

        # Complete generic processing values with acquirer-specific values
        processing_values.update(self._get_specific_processing_values(processing_values))
        _logger.info(
            f"payment.transaction._get_processing_values for acquirer with id "
            f"{self.acquirer_id.id}:\n{pprint.pformat(processing_values)}",
        )

        # Render the html form for the redirect flow if available
        if self.acquirer_id.redirect_template_view_id:
            rendering_values = self._get_specific_rendering_values(processing_values)
            redirect_form_html = self.acquirer_id.redirect_template_view_id._render(
                rendering_values, engine='ir.qweb'
            )
            processing_values.update(redirect_form_html=redirect_form_html)

        return processing_values

    def _get_specific_processing_values(self, _processing_values):
        """ Return a dict of acquirer-specific values used to process the transaction.

        For an acquirer to add its own processing values, it must overwrite this method and return a
        dict of acquirer-specific values based on the generic values returned by this method.
        Acquirer-specific values take precedence over those of the dict of generic processing
        values.

        :param dict _processing_values: The generic processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        return dict()

    def _get_specific_rendering_values(self, _processing_values):
        """ Return a dict of acquirer-specific values used to render the redirect form.

        For an acquirer to add its own rendering values, it must overwrite this method and return a
        dict of acquirer-specific values based on the processing values (acquirer-specific
        processing values included).

        :param dict _processing_values: The processing values of the transaction
        :return: The dict of acquirer-specific rendering values
        :rtype: dict
        """
        return dict()

    def _send_payment_request(self):
        """ Request the provider of the acquirer handling the transactions to execute the payment.

        For an acquirer to support tokenization, it must override this method and call it to log the
        'sent' message, then request a money transfer to its provider.

        :return: None
        """
        self._log_sent_message()
    
    @api.model
    def _handle_feedback_data(self, provider, data):
        """ Handle the feedback data sent by the provider.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found, and the feedback processing result
        :rtype: tuple[recordset of `payment.transaction`, bool]
        """
        feedback_result = True
        tx = self._get_tx_from_data(provider, data)
        if tx:
            invalid_parameters = tx._get_invalid_parameters(data)
            # TODO ANV check later if can be merged in _process_feedback_data (raise if needed)
            if invalid_parameters:
                error_message = "received incorrect transaction data:"
                for parameter in invalid_parameters:
                    expected_value, received_value = invalid_parameters[parameter]
                    error_message += f"\n\t{parameter}: " \
                                     f"expected {expected_value} ; received {received_value}"
                _logger.error(error_message)
                feedback_result = False
            else:
                feedback_result = tx._process_feedback_data(data)
                tx._execute_callback()
        else:
            pass  # The transaction might not be recorded in Odoo in some acquirer-specific flows
        return tx, feedback_result

    @api.model
    def _get_tx_from_data(self, provider, data):
        """ Find and return the transaction based on the transaction data and on the acquirer.

        For an acquirer to handle transaction post-processing, it must overwrite this method and
        return the transaction that is identified by the data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The transaction data sent by the acquirer
        :return: The payment.transaction record if found, else an empty recordset
        :rtype: recordset of `payment.transaction`
        """
        return self

    def _get_invalid_parameters(self, data):
        """ List acquirer-specific invalid parameters and return them.

        For an acquirer to handle transaction post-processing, it must overwrite this method and
        return the invalid parameters found in the data.

        Note: self.ensure_one()

        :param dict data: The transaction data sent by the acquirer
        :return: The dict of invalid parameters whose entries have the name of the parameter
                 as key and a tuple (expected value, received value) as value
        :rtype: dict
        """
        self.ensure_one()
        return dict()

    def _process_feedback_data(self, data):
        """ Process the feedback data for the current transaction and make necessary updates.

        For an acquirer to handle transaction post-processing, it must overwrite this method and
        process the feedback data, then return whether the processing was successfully done.

        Note: self.ensure_one()

        :param dict data: The transaction data sent by the acquirer
        :return: True if the feedback is successfully processed, False otherwise
        :rtype: bool
        """
        self.ensure_one()
        return True

    def _set_pending(self):
        """ Update the transactions' state to 'pending'.

        :return: None
        """
        allowed_states = ('draft',)
        target_state = 'pending'
        txs_to_process = self._update_state(allowed_states, target_state)
        txs_to_process._log_received_message()

    def _set_authorized(self):
        """ Update the transactions' state to 'authorized'.

        :return: None
        """
        allowed_states = ('draft', 'pending')
        target_state = 'authorized'
        txs_to_process = self._update_state(allowed_states, target_state)
        txs_to_process._log_received_message()

    def _set_done(self):
        """ Update the transactions' state to 'done'.

        :return: None
        """
        allowed_states = ('draft', 'authorized', 'pending', 'error')
        target_state = 'done'
        txs_to_process = self._update_state(allowed_states, target_state)
        txs_to_process._log_received_message()

    def _set_canceled(self):
        """ Update the transactions' state to 'cancel'.

        :return: None
        """
        allowed_states = ('draft', 'authorized')
        target_state = 'cancel'
        txs_to_process = self._update_state(allowed_states, target_state, update_message=None)
        # Cancel the existing payments
        txs_to_process.mapped('payment_id').action_cancel()
        txs_to_process._log_received_message()

    def _set_error(self, error_message):
        """ Update the transactions' state to 'error'.

        :return: None
        """
        allowed_states = ('draft', 'authorized', 'pending')
        target_state = 'error'
        txs_to_process = self._update_state(
            allowed_states, target_state, update_message=error_message
        )
        txs_to_process._log_received_message()

    def _update_state(self, allowed_states, target_state, update_message=""):
        """ Update the transactions' state according to the specified allowed and target states.

        :param tuple[str] allowed_states: The allowed source states for the target state
        :param string target_state: The target state
        :param string update_message: The message to write in `state_message`. If `None`, the
                                      previous message is *not* overwritten
        :return: The recordset of transactions whose state was correctly updated
        :rtype: recordset of `payment.transaction`
        """

        def _classify_by_state(_transactions):
            """Classify the transactions according to their current state.

            For each transaction of the current recordset, if:
                - The state is an allowed state: the transaction is flagged as 'to process'.
                - The state is equal to the target state: the transaction is flagged as 'processed'.
                - The state matches none of above: the transaction is flagged as 'in wrong state'.

            :param recordset _transactions: The transactions to classify, as a `payment.transaction`
                                            recordset
            :return: A 3-items tuple of recordsets of classified transactions, in this order:
                     transactions 'to process', transactions 'processed',
                     transactions 'in wrong state'
            :rtype: tuple(recordset)
            """
            _txs_to_process = _transactions.filtered(lambda _tx: _tx.state in allowed_states)
            _txs_already_processed = _transactions.filtered(lambda _tx: _tx.state == target_state)
            _txs_wrong_state = _transactions - _txs_to_process - _txs_already_processed

            return _txs_to_process, _txs_already_processed, _txs_wrong_state

        txs_to_process, txs_already_processed, txs_wrong_state = _classify_by_state(self)
        for tx in txs_already_processed:
            _logger.info(
                f"tried to write tx state with same value (ref: {tx.reference}, state: {tx.state}"
            )
        for tx in txs_wrong_state:
            _logger.warning(
                f"tried to write tx state with illegal value (ref: {tx.reference}, "
                f"previous state {tx.state}, target state: {target_state}, "
                f"expected previous state to be in: {allowed_states})")
        write_values = {
            'state': target_state,
            'last_state_change': fields.Datetime.now(),
        }
        if update_message is not None:
            write_values['state_message'] = update_message
        txs_to_process.write(write_values)
        return txs_to_process

    def _execute_callback(self):
        """ Execute the callbacks defined on the transactions.

        Callbacks that have already been executed are silently ignored. This case can happen when a
        transaction is first authorized before being confirmed, for instance. In this case, both
        status updates try to execute the callback.

        Only successful callbacks are marked as done. This allows callbacks to reschedule themselves
        should the conditions not be met in the present call.

        :return: None
        """
        for tx in self.filtered(lambda t: not t.callback_is_done):
            model_id_sudo = tx.sudo().callback_model_id  # Only use sudo to check, not to execute
            res_id = tx.sudo().callback_res_id
            method = tx.sudo().callback_method
            if not (model_id_sudo and res_id and method):
                continue  # Ignore undefined or not properly defined callbacks

            valid_callback_hash = self._generate_callback_hash(model_id_sudo.id, res_id, method)
            if not consteq(ustr(valid_callback_hash), tx.callback_hash):
                _logger.warning(f"invalid callback signature for transaction with id {tx.id}")
                continue  # Ignore tampered callbacks

            record = self.env[model_id_sudo.model].browse(res_id).exists()
            if not record:
                _logger.warning(
                    f"invalid callback record {model_id_sudo.model}.{res_id} for transaction with "
                    f"id {tx.id}"
                )
                continue  # Ignore invalidated callbacks

            success = getattr(record, method)(tx)  # Execute the callback
            tx.callback_is_done = success or success is None  # Missing returns are successful

    def _send_refund_request(self):
        """ Request the provider of the acquirer handling the transaction to refund it.

        For an acquirer to support tokenization, it must override this method and request a refund
        to its provider.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()

    def _send_capture_request(self):
        """ Request the provider of the acquirer handling the transaction to capture it.

        For an acquirer to support authorization, it must override this method and request a capture
        to its provider.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()

    def _send_void_request(self):
        """ Request the provider of the acquirer handling the transaction to void it.

        For an acquirer to support authorization, it must override this method and request the
        transaction to be voided to its provider.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()

    #=== BUSINESS METHODS - POST-PROCESSING ===#

    def _get_post_processing_values(self):
        """ Return a dict of values used to display the status of the transaction.

        For an acquirer to handle transaction status display, it must override this method and
        return a dict of values. Acquirer-specific values take precedence over those of the dict of
        generic post-processing values.

        The returned dict contains the following entries:
            - provider: The provider of the acquirer
            - reference: The reference of the transaction
            - amount: The rounded amount of the transaction
            - currency_id: The currency of the transaction, as a res.currency id
            - state: The transaction state: draft, pending, authorized, done, cancel or error
            - state_message: The information message about the state
            - is_post_processed: Whether the transaction has already been post-processed
            - landing_route: The route the user is redirected to after the transaction
            - Additional acquirer-specific entries

        Note: self.ensure_one()

        :return: The dict of processing values
        :rtype: dict
        """
        self.ensure_one()

        post_processing_values = {
            'provider': self.acquirer_id.provider,
            'reference': self.reference,
            'amount': self.amount,
            'currency_code': self.currency_id.name,
            'state': self.state,
            'state_message': self.state_message,
            'is_validation': self.operation == 'validation',
            'is_post_processed': self.is_post_processed,
            'validation_route': self.validation_route,
            'landing_route': self.landing_route,
        }
        _logger.info(
            f"payment.transaction._get_post_processing_values for acquirer with id "
            f"{self.acquirer_id.id}:\n{pprint.pformat(post_processing_values)}",
        )
        return post_processing_values

    def _finalize_post_processing(self):
        """ Trigger the final post-processing tasks and mark the transactions as post-processed.

        :return: None
        """
        self._reconcile_after_done()
        self._log_received_message()  # 2nd call to link the created account.payment in the chatter
        self.is_post_processed = True

    def _cron_finalize_post_processing(self):
        """ Finalize the post-processing of recently done transactions not handled by the client.

        :return: None
        """
        txs_to_post_process = self
        if not txs_to_post_process:
            # Let the client post-process transactions so that they remain available in the portal
            client_handling_limit_date = datetime.now() - relativedelta.relativedelta(minutes=1)
            # Don't try forever to post-process a transaction that doesn't go through
            retry_limit_date = datetime.now() - relativedelta.relativedelta(days=2)
            # Retrieve all transactions matching the criteria for post-processing
            txs_to_post_process = self.search([
                ('state', '=', 'done'),
                ('is_post_processed', '=', False),
                ('last_state_change', '<=', client_handling_limit_date),
                ('last_state_change', '>=', retry_limit_date),
            ])
        for tx in txs_to_post_process:
            try:
                tx._finalize_post_processing()
                self.env.cr.commit()
            except psycopg2.OperationalError:  # A collision of accounting sequences occurred
                request.env.cr.rollback()  # Rollback and try later
            except Exception as e:
                _logger.exception(
                    f"encountered an error while post-processing transaction with id {tx.id}. "
                    f"exception: \"{e}\""
                )
                self.env.cr.rollback()

    def _reconcile_after_done(self):
        """ Post relevant fiscal documents and create missing payments.

        :return: None
        """
        # Validate invoices automatically once the transaction is confirmed
        self.mapped('invoice_ids').filtered(lambda inv: inv.state == 'draft').action_post()

        # Create and post missing payments
        for tx in self.filtered(lambda t: not t.payment_id):
            tx._create_payment()

    def _create_payment(self, **extra_create_values):
        """Create an `account.payment` record for the current transaction.

        If the transaction is linked to some invoices, their reconciliation is done automatically.

        Note: self.ensure_one()

        :param dict extra_create_values: Optional extra create values
        :return: The created payment
        :rtype: recordset of `account.payment`
        """
        self.ensure_one()

        payment_values = {
            'amount': self.amount,
            'payment_type': 'inbound' if self.amount > 0 else 'outbound',
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_type': 'customer',
            'journal_id': self.acquirer_id.journal_id.id,
            'company_id': self.acquirer_id.company_id.id,
            'payment_method_id': self.env.ref('payment.account_payment_method_electronic_in').id,
            'payment_token_id': self.token_id.id,
            'payment_transaction_id': self.id,
            'ref': self.reference,
            **extra_create_values,
        }
        payment = self.env['account.payment'].create(payment_values)
        payment.action_post()

        # Track the payment to make a one2one.
        self.payment_id = payment

        if self.invoice_ids:
            self.invoice_ids.filtered(lambda inv: inv.state == 'draft').action_post()

            (payment.line_ids + self.invoice_ids.line_ids).filtered(
                lambda line: line.account_id == payment.destination_account_id
                and not line.reconciled
            ).reconcile()

        return payment

    #=== BUSINESS METHODS - GETTERS ===#

    def _get_linked_documents(self):
        """ Return the invoices linked to the transaction.

        For a module to implement payments and link documents to a transaction, it must override
        this method and return the recordset of linked documents, if any, or the result of super.

        Note: self.ensure_one()

        :return: The invoices linked to the transaction
        :rtype: recordset of `account.move`
        """
        self.ensure_one()
        return self.invoice_ids

    def _get_last(self):
        """ Return the last transaction of the recordset.

        :return: The last transaction of the recordset, sorted by id
        :rtype: recordset of `payment.transaction`
        """
        return self.filtered(lambda t: t.state != 'draft').sorted()[:1]

    #=== BUSINESS METHODS - LOGGING ===#

    def _log_sent_message(self):
        """ Log in the chatter of relevant documents that the transactions have been initiated.

        :return: None
        """
        for tx in self:
            linked_documents = tx._get_linked_documents()
            message = tx._get_sent_message()
            for document in linked_documents:
                document.message_post(body=message)

    def _get_sent_message(self):
        """ Return the message stating that the transaction has been requested.

        Note: self.ensure_one()

        :return: The 'transaction sent' message
        :rtype: str
        """
        self.ensure_one()

        # Choose the message based on the payment flow and provider
        if self.token_id:  # The payment is made by token
            message = _(
                "A transaction with reference %(ref)s has been initiated using the payment method "
                "%(token_name)s (%(acq_name)s).",
                ref=self.reference, token_name=self.token_id.name, acq_name=self.acquirer_id.name
            )
        elif self.provider in ('manual', 'transfer'):  # The payment is made by direct transfer
            # The reference of the transaction is not logged since it remains in draft forever
            message = _(
                "The customer has selected %(acq_name)s to make the payment.",
                acq_name=self.acquirer_id.name
            )  # TODO ANV check that payment_transfer indeed uses this, or remove
        else:  # The payment is direct and initiated through an inline form
            message = _(
                "A transaction with reference %(ref)s has been initiated (%(acq_name)s).",
                ref=self.reference, acq_name=self.acquirer_id.name
            )  # TODO ANV check that at least one acquirer uses this, or remove
        return message

    def _log_received_message(self):
        """ Log in the chatter of relevant documents that the transactions have been received.

        A transaction is 'received' when a response is received from the provider of the acquirer
        handling the transaction.

        :return: None
        """
        for tx in self.filtered(lambda t: t.provider not in ('manual', 'transfer')):  # TODO override and filter in payment_transfer
            linked_documents = tx._get_linked_documents()
            message = tx._get_received_message()
            for document in linked_documents:
                document.message_post(body=message)

    def _get_received_message(self):
        """ Return the message stating that the transaction has been received by the provider.

        Note: self.ensure_one()
        """
        self.ensure_one()

        formatted_amount = formatLang(self.env, self.amount, currency_obj=self.currency_id)
        if self.state == 'pending':
            message = _(
                "The transaction with reference %(ref)s for %(amount)s is pending (%(acq_name)s).",
                ref=self.reference, amount=formatted_amount, acq_name=self.acquirer_id.name
            )
        elif self.state == 'authorized':
            message = _(
                "The transaction with reference %(ref)s for %(amount)s has been authorized "
                "(%(acq_name)s).", ref=self.reference, amount=formatted_amount,
                acq_name=self.acquirer_id.name
            )
        elif self.state == 'done':
            message = _(
                "The transaction with reference %(ref)s for %(amount)s has been confirmed "
                "(%(acq_name)s).", ref=self.reference, amount=formatted_amount,
                acq_name=self.acquirer_id.name
            )
            if self.payment_id:
                message += _(
                    "\nThe related payment is posted: %s",
                    self.payment_id._get_payment_chatter_link()
                )
        elif self.state == 'error':
            message = _(
                "The transaction with reference %(ref)s for %(amount)s encountered an error"
                " (%(acq_name)s).",
                ref=self.reference, amount=formatted_amount, acq_name=self.acquirer_id.name
            )
            if self.state_message:
                message += _("\nError: %s", self.state_message)
        else:
            message = _(
                "The transaction with reference %(ref)s for %(amount)s is canceled (%(acq_name)s).",
                ref=self.reference, amount=formatted_amount, acq_name=self.acquirer_id.name
            )
            if self.state_message:
                message += _("\nReason: %s", self.state_message)
        return message
