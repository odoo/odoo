# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    payment_id = fields.Many2one(
        string="Payment", comodel_name='account.payment', readonly=True)

    invoice_ids = fields.Many2many(
        string="Invoices", comodel_name='account.move', relation='account_invoice_transaction_rel',
        column1='transaction_id', column2='invoice_id', readonly=True, copy=False,
        domain=[('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'))])
    invoices_count = fields.Integer(string="Invoices Count", compute='_compute_invoices_count')

    #=== COMPUTE METHODS ===#

    @api.depends('invoice_ids')
    def _compute_invoices_count(self):
        self.env.cr.execute(
            '''
            SELECT transaction_id, count(invoice_id)
            FROM account_invoice_transaction_rel
            WHERE transaction_id IN %s
            GROUP BY transaction_id
            ''',
            [tuple(self.ids)]
        )
        tx_data = dict(self.env.cr.fetchall())  # {id: count}
        for tx in self:
            tx.invoices_count = tx_data.get(tx.id, 0)

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

    #=== BUSINESS METHODS - PAYMENT FLOW ===#

    @api.model
    def _compute_reference_prefix(self, provider_code, separator, **values):
        """ Compute the reference prefix from the transaction values.

        If the `values` parameter has an entry with 'invoice_ids' as key and a list of (4, id, O) or
        (6, 0, ids) X2M command as value, the prefix is computed based on the invoice name(s).
        Otherwise, an empty string is returned.

        Note: This method should be called in sudo mode to give access to documents (INV, SO, ...).

        :param str provider_code: The code of the provider handling the transaction
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
        return super()._compute_reference_prefix(provider_code, separator, **values)

    def _set_canceled(self, state_message=None):
        """ Update the transactions' state to 'cancel'.

        :param str state_message: The reason for which the transaction is set in 'cancel' state
        :return: updated transactions
        :rtype: `payment.transaction` recordset
        """
        processed_txs = super()._set_canceled(state_message)
        # Cancel the existing payments
        processed_txs.payment_id.action_cancel()
        return processed_txs

    #=== BUSINESS METHODS - POST-PROCESSING ===#

    def _reconcile_after_done(self):
        """ Post relevant fiscal documents and create missing payments.

        As there is nothing to reconcile for validation transactions, no payment is created for
        them. This is also true for validations with a validity check (transfer of a small amount
        with immediate refund) because validation amounts are not included in payouts.

        :return: None
        """
        super()._reconcile_after_done()

        # Validate invoices automatically once the transaction is confirmed
        self.invoice_ids.filtered(lambda inv: inv.state == 'draft').action_post()

        # Create and post missing payments for transactions requiring reconciliation
        for tx in self.filtered(lambda t: t.operation != 'validation' and not t.payment_id):
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

        payment_method_line = self.provider_id.journal_id.inbound_payment_method_line_ids\
            .filtered(lambda l: l.code == self.provider_code)
        payment_values = {
            'amount': abs(self.amount),  # A tx may have a negative amount, but a payment must >= 0
            'payment_type': 'inbound' if self.amount > 0 else 'outbound',
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.commercial_partner_id.id,
            'partner_type': 'customer',
            'journal_id': self.provider_id.journal_id.id,
            'company_id': self.provider_id.company_id.id,
            'payment_method_line_id': payment_method_line.id,
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

    #=== BUSINESS METHODS - LOGGING ===#

    def _log_message_on_linked_documents(self, message):
        """ Log a message on the payment and the invoices linked to the transaction.

        For a module to implement payments and link documents to a transaction, it must override
        this method and call super, then log the message on documents linked to the transaction.

        Note: self.ensure_one()

        :param str message: The message to be logged
        :return: None
        """
        self.ensure_one()
        self = self.with_user(SUPERUSER_ID)  # Log messages as 'OdooBot'
        if self.source_transaction_id.payment_id:
            self.source_transaction_id.payment_id.message_post(body=message)
            for invoice in self.source_transaction_id.invoice_ids:
                invoice.message_post(body=message)
        for invoice in self.invoice_ids:
            invoice.message_post(body=message)

    #=== BUSINESS METHODS - POST-PROCESSING ===#

    def _finalize_post_processing(self):
        """ Override of `payment` to write a message in the chatter with the payment and transaction
        references.

        :return: None
        """
        super()._finalize_post_processing()
        for tx in self.filtered('payment_id'):
            message = _(
                "The payment related to the transaction with reference %(ref)s has been posted: "
                "%(link)s", ref=tx.reference, link=tx.payment_id._get_html_link()
            )
            tx._log_message_on_linked_documents(message)
