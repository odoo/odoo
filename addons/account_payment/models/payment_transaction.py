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
        tx_data = {}
        if self.ids:
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

    def _set_canceled(self, state_message=None, **kwargs):
        """ Update the transactions' state to 'cancel'.

        :param str state_message: The reason for which the transaction is set in 'cancel' state
        :return: updated transactions
        :rtype: `payment.transaction` recordset
        """
        processed_txs = super()._set_canceled(state_message, **kwargs)
        # Cancel the existing payments
        processed_txs.payment_id.action_cancel()
        return processed_txs

    #=== BUSINESS METHODS - POST-PROCESSING ===#

    def _reconcile_after_done(self):
        """ Post relevant fiscal documents and create missing payments.

        As there is nothing to reconcile for validation transactions, no payment is created for
        them. This is also true for validations with a validity check (transfer of a small amount
        with immediate refund) because validation amounts are not included in payouts.

        As the reconciliation is done in the child transactions for partial voids and captures, no
        payment is created for their source transactions.

        :return: None
        """
        super()._reconcile_after_done()

        # Validate invoices automatically once the transaction is confirmed
        self.invoice_ids.filtered(lambda inv: inv.state == 'draft').action_post()

        # Create and post missing payments for transactions requiring reconciliation
        for tx in self.filtered(lambda t: t.operation != 'validation' and not t.payment_id):
            if not any(child.state in ['done', 'cancel'] for child in tx.child_transaction_ids):
                tx.with_company(tx.company_id)._create_payment()

    def _create_payment(self, **extra_create_values):
        """Create an `account.payment` record for the current transaction.

        If the transaction is linked to some invoices, their reconciliation is done automatically.

        Note: self.ensure_one()

        :param dict extra_create_values: Optional extra create values
        :return: The created payment
        :rtype: recordset of `account.payment`
        """
        self.ensure_one()

        reference = (f'{self.reference} - '
                     f'{self.partner_id.display_name or ""} - '
                     f'{self.provider_reference or ""}'
                    )

        payment_method_line = self.provider_id.journal_id.inbound_payment_method_line_ids\
            .filtered(lambda l: l.payment_provider_id == self.provider_id)
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
            'ref': reference,
            'write_off_line_vals': [],
            **extra_create_values,
        }

        payment_term_lines = self.invoice_ids.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        if payment_term_lines:
            payment_values['destination_account_id'] = payment_term_lines[0].account_id.id

        for invoice in self.invoice_ids:
            next_payment_values = invoice._get_invoice_next_payment_values()
            if next_payment_values['installment_state'] == 'epd' and self.amount == next_payment_values['amount_due']:
                aml = next_payment_values['epd_line']
                epd_aml_values_list = [({
                    'aml': aml,
                    'amount_currency': -aml.amount_residual_currency,
                    'balance': -aml.balance,
                })]
                open_balance = next_payment_values['epd_discount_amount']
                early_payment_values = self.env['account.move']._get_invoice_counterpart_amls_for_early_payment_discount(epd_aml_values_list, open_balance)
                for aml_values_list in early_payment_values.values():
                    if aml_values_list:
                        aml_vl = aml_values_list[0]
                        aml_vl['partner_id'] = self.partner_id.id
                        payment_values['write_off_line_vals'] += [aml_vl]

        payment = self.env['account.payment'].create(payment_values)
        payment.action_post()

        # Track the payment to make a one2one.
        self.payment_id = payment

        # Reconcile the payment with the source transaction's invoices in case of a partial capture.
        if self.operation == self.source_transaction_id.operation:
            invoices = self.source_transaction_id.invoice_ids
        else:
            invoices = self.invoice_ids
        if invoices:
            invoices.filtered(lambda inv: inv.state == 'draft').action_post()

            (payment.line_ids + invoices.line_ids).filtered(
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
        author = self.env.user.partner_id if self.env.uid == SUPERUSER_ID else self.partner_id
        if self.source_transaction_id:
            for invoice in self.source_transaction_id.invoice_ids:
                invoice.message_post(body=message, author_id=author.id)
            payment_id = self.source_transaction_id.payment_id
            if payment_id:
                payment_id.message_post(body=message, author_id=author.id)
        for invoice in self.invoice_ids:
            invoice.message_post(body=message, author_id=author.id)

    #=== BUSINESS METHODS - POST-PROCESSING ===#

    def _finalize_post_processing(self):
        """ Override of `payment` to write a message in the chatter with the payment and transaction
        references.

        :return: None
        """
        super()._finalize_post_processing()
        for tx in self.filtered('payment_id'):
            message = _("The payment related to the transaction with reference %(ref)s has been posted: %(link)s",
                ref=tx.reference, link=tx.payment_id._get_html_link(),
            )
            tx._log_message_on_linked_documents(message)
