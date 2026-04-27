# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time, timedelta

from odoo import api, fields, models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # used to control the renewal flow based on the transaction state
    renewal_state = fields.Selection([('draft', 'Draft'),
                                      ('pending', 'Pending'),
                                      ('authorized', 'Authorized'),
                                      ('cancel', 'Refused')], compute='_compute_renewal_state')
    subscription_action = fields.Selection([
        ('automatic_send_mail', 'Send Mail (automatic payment)'),
        ('manual_send_mail', 'Send Mail (manual payment)'),
        ('assign_token', 'Assign Token'),
    ])

    @api.depends('state')
    def _compute_renewal_state(self):
        for tx in self:
            if tx.state in ['draft', 'pending']:
                renewal_state = tx.state
            elif tx.state in ('done', 'authorized'):
                renewal_state = 'authorized'
            else:
                # tx state in cancel or error
                renewal_state = 'cancel'
            tx.renewal_state = renewal_state

    ####################
    # Business Methods #
    ####################

    def _get_mandate_values(self):
        """ Override of `payment` to inject subscription-specific data into the mandate values.

        Note: `self.ensure_one()`

        :return: The dict of module-specific mandate values.
        :rtype: dict
        """
        mandate_values = super()._get_mandate_values()
        if len(self.sale_order_ids) != 1 or not self.sale_order_ids.is_subscription:
            return mandate_values

        # Convert start and end dates into datetime by setting the time to midnight.
        # Payment providers require the start_datetime of the mandate to not be lesser than yesterday
        # e.g., stripe: https://docs.stripe.com/api/payment_intents/create#create_payment_intent-payment_method_options-card-mandate_options-start_date
        current_time = fields.Datetime.now()
        start_date = self.sale_order_ids.start_date or current_time
        start_datetime = max(
            datetime.combine(start_date, time()),
            current_time - timedelta(days=1)
        )
        end_datetime = self.sale_order_ids.end_date \
            and datetime.combine(self.sale_order_ids.end_date, time())
        mandate_values.update({
            # The maximum amount that can be charged with the mandated.
            'amount': self.sale_order_ids.amount_total,
            'MRR': self.sale_order_ids.recurring_monthly,
            'start_datetime': start_datetime,
            'end_datetime': end_datetime,
            'recurrence_unit': self.sale_order_ids.plan_id.billing_period_unit,
            'recurrence_duration': self.sale_order_ids.plan_id.billing_period_value,
        })
        return mandate_values

    def _create_or_link_to_invoice(self):
        tx_to_invoice = self.env['payment.transaction']
        for tx in self:
            if len(tx.sale_order_ids) > 1 or tx.invoice_ids or not tx.sale_order_ids.is_subscription:
                continue
            elif tx.renewal_state in ['draft', 'pending', 'cancel']:
                # tx should be in an authorized renewal_state otherwise _reconcile_after_done will not be called
                # but this is a safety to prevent issue when the code is called manually
                continue
            tx_to_invoice += tx
            tx._cancel_draft_invoices()

        tx_to_invoice._invoice_sale_orders()
        tx_to_invoice.invoice_ids.with_company(self.company_id)._post()
        if not self.env.context.get('skip_sale_auto_invoice_send'):
            tx_to_invoice.filtered(lambda t: not t.subscription_action).invoice_ids.transaction_ids._send_invoice()

    def _get_invoiced_subscription_transaction(self):
        # create the invoices for the transactions that are not yet linked to invoice
        # `_do_payment` do link an invoice to the payment transaction
        # calling `super()._invoice_sale_orders()` would create a second invoice for the next period
        # instead of the current period and would reconcile the payment with the new invoice
        def _filter_invoiced_subscription(self):
            self.ensure_one()
            # we look for tx with one invoice
            if len(self.invoice_ids) != 1:
                return False
            return any(self.invoice_ids.mapped('invoice_line_ids.sale_line_ids.order_id.is_subscription'))

        return self.filtered(_filter_invoiced_subscription)

    def _get_partial_payment_subscription_transaction(self):
        # filter transaction which are only a partial payment of subscription and that don't fulfill a payment that
        # is already existing
        tx_with_partial_payments = self.env["payment.transaction"]
        for tx in self:
            order = tx.sale_order_ids.filtered(lambda so: so.state == 'sale')
            if not any(order.mapped('is_subscription')):
                # not subscription related
                continue
            elif len(order) > 1:
                # we don't support multiple order per tx. Accounting should invoice manually
                tx_with_partial_payments |= tx
            elif order.currency_id.compare_amounts(
                    sum(order.transaction_ids.filtered(lambda tx: tx.renewal_state == 'authorized' and not tx.invoice_ids).mapped('amount')),
                    order.amount_total
                ) != 0:
                # The payment amount and other unused transactions will confirm and pay the invoice
                tx_with_partial_payments |= tx
        return tx_with_partial_payments

    def _invoice_sale_orders(self):
        """ Override of payment to increase next_invoice_date when needed. """
        transaction_to_invoice = self - self._get_invoiced_subscription_transaction()
        transaction_to_invoice -= self._get_partial_payment_subscription_transaction()
        # Update the next_invoice_date of SOL when the payment_mode is 'success_payment'
        # We have to do it here because when a client confirms and pay a SO from the portal with success_payment
        # The next_invoice_date won't be updated by the reconcile_pending_transaction callback (do_payment is not called)
        # Create invoice
        res = super(PaymentTransaction, transaction_to_invoice)._invoice_sale_orders()
        return res

    def _post_process(self):
        """ Override of `payment` to add Subscriptions-specific logic to the post-processing.

        In particular, for confirmed transactions we handle reconciliation for subscription's
        validation transaction references. For cancelled or error transactions, we call
        `_handle_unsuccessful_transaction`. If any subscription got paid, trigger the post
        subscription actions method in batch.

        :return: None
        """
        # Avoid post processing tx whose SO is still being processed by the invoice cron
        process_tx = self.filtered(lambda tx: not any(tx.sale_order_ids.mapped('is_invoice_cron')))
        res = super(PaymentTransaction, process_tx)._post_process()
        any_paid_subscription = False
        close_reasons_ids = self.env['sale.order.close.reason']._get_reason_to_reopen()
        for tx in process_tx:
            orders = tx.sale_order_ids or tx.invoice_ids.line_ids.subscription_id
            subscriptions = orders.filtered(lambda order: order.is_subscription)
            if tx.state == 'done' and len(subscriptions) > 0:
                if tx.operation != 'validation':
                    tx.with_context(forced_invoice=True)._create_or_link_to_invoice()
                any_paid_subscription = True
                # Re-open churned subscriptions after payment.
                subscriptions.filtered(
                    lambda sub:
                        sub.subscription_state == '6_churn' and
                        sub.close_reason_id.id in close_reasons_ids and
                        (tx.last_state_change.date() - timedelta(days=sub.plan_id.auto_close_limit)) <= sub.next_invoice_date
                ).set_open()
            elif tx.state in ('error', 'cancel'):
                tx._handle_unsuccessful_transaction()
        if any_paid_subscription:
            self._post_subscription_action()
        return res


    def _post_subscription_action(self):
        """
        Execute the subscription action once the transaction is in an acceptable state
        This will also reopen the order and remove the payment pending state.
        Partial payment should not have a subscription_action defined and therefore should not reopen the order.
        """
        reopen_reasons_ids = self.env['sale.order.close.reason']._get_reason_to_reopen()
        for tx in self:
            orders = tx.sale_order_ids
            # quotation subscription paid on portal have pending transactions
            orders.pending_transaction = False
            if not tx.subscription_action or tx.renewal_state != 'authorized':
                # We don't assign failing tokens, and we don't send emails
                continue
            if tx.subscription_action == 'assign_token':
                orders._assign_token(tx)
            if tx.operation == 'validation':
                # validation transaction have the `assign_token` `subscription_action`
                # Once the token is assigned, we are done because we don't send emails in that case.
                continue
            reopen_ids = []
            for order in orders:
                if order.subscription_state != '6_churn' or (not order.close_reason_id or order.close_reason_id.id in reopen_reasons_ids):
                    reopen_ids.append(order.id)
            self.env['sale.order'].browse(reopen_ids).set_open()
            if tx.subscription_action:
                automatic = tx.subscription_action == 'automatic_send_mail'
                for order in orders:
                    order._subscription_post_success_payment(tx, tx.invoice_ids, automatic=automatic)

    def _send_invoice(self):
        subscription_action_txs = self.filtered(lambda tx: (
            tx.operation != 'validation'
            and tx.subscription_action
            and tx.renewal_state == 'authorized'
            and not tx.is_post_processed
        ))
        # we're going to send subscription invoices with a specific
        # email, so skip those from here to not send them a second time
        return super(PaymentTransaction, self - subscription_action_txs)._send_invoice()

    def _set_done(self, **kwargs):
        orders = self.sale_order_ids
        # Flag of subscription processed in the cron is removed in the cron to avoid concurrent updates
        orders.filtered(lambda so: so.is_subscription and not so.is_invoice_cron).payment_exception = False
        return super()._set_done(**kwargs)

    def _set_pending(self, **kwargs):
        orders = self.sale_order_ids
        # Flag of subscription processed in the cron is removed in the cron to avoid concurrent updates
        orders.filtered(lambda so: so.is_subscription and not so.is_invoice_cron).payment_exception = False
        return super()._set_pending(**kwargs)

    def _set_authorized(self, **kwargs):
        orders = self.sale_order_ids
        # Flag of subscription processed in the cron is removed in the cron to avoid concurrent updates
        orders.filtered(lambda so: so.is_subscription and not so.is_invoice_cron).payment_exception = False
        return super()._set_authorized(**kwargs)

    def _handle_unsuccessful_transaction(self):
        """ Unset pending transactions for subscriptions and cancel their draft invoices. """
        for transaction in self:
            subscriptions = transaction.sale_order_ids.filtered('is_subscription')
            if subscriptions:
                # Flag of subscription processed in the cron is removed in the cron to avoid concurrent updates
                subscriptions.filtered(lambda so: not so.is_invoice_cron).pending_transaction = False
                transaction._cancel_draft_invoices()

    def _cancel_draft_invoices(self):
        """ Cancel draft invoices attached to subscriptions. """
        self.ensure_one()
        subscriptions = self.sale_order_ids.filtered('is_subscription')
        draft_invoices = subscriptions.order_line.invoice_lines.move_id.filtered(lambda am: am.state == 'draft')
        if draft_invoices:
            draft_invoices.button_cancel()

    def _get_invoices_to_notify(self):
        """ Override `payment` to filter out invoices whose logging is already handled by the cron.

        This prevents deadlocks from happening in the case where:
        1. the cron creates invoices linked to the transaction;
        2. initiate the payment;
        3. commits the cursor;
        4. deletes the linked invoices because the payment didn't go through;
        5. the payment webhook tries to log the payment failure on the committed-but-now-deleted
           invoices.
        """
        return self.invoice_ids.filtered(
            lambda invoice: not any(
                o.is_invoice_cron for o in invoice.invoice_line_ids.sale_line_ids.order_id
            )
        )
