# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time

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
        start_datetime = self.sale_order_ids.start_date \
            and datetime.combine(self.sale_order_ids.start_date, time())
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
        tx_to_invoice.invoice_ids._post()
        tx_to_invoice.filtered(lambda t: not t.subscription_action).invoice_ids.transaction_ids._send_invoice()

    def _reconcile_after_done(self):
        # override to force invoice creation if the transaction is done for a subscription
        # We don't take care of the sale.automatic_invoice parameter in that case.
        res = super()._reconcile_after_done()
        self.filtered(lambda tx: tx.operation != 'validation').with_context(forced_invoice=True)._create_or_link_to_invoice()
        self._post_subscription_action()
        return res

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

    def _finalize_post_processing(self):
        """ Override of `payment` to handle reconcilation for subscription's validation transaction.
        references.
        `super()._finalize_post_processing` never call `_reconcile_after_done` on validation tx.
        We explicitely calls it here to make sure the token is assigned.

        :return: None
        """
        self.filtered(lambda tx: tx.operation == 'validation' and tx.sale_order_ids.is_subscription)._reconcile_after_done()
        super()._finalize_post_processing()

    def _post_subscription_action(self):
        """
        Execute the subscription action once the transaction is in an acceptable state
        This will also reopen the order and remove the payment pending state.
        Partial payment should not have a subscription_action defined and therefore should not reopen the order.
        """
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
            orders.set_open()
            orders._send_success_mail(tx.invoice_ids, tx)
            if tx.subscription_action in ['manual_send_mail', 'automatic_send_mail']:
                automatic = tx.subscription_action == 'automatic_send_mail'
                for order in orders:
                    order._subscription_post_success_payment(tx, tx.invoice_ids, automatic=automatic)

    def _set_done(self, **kwargs):
        self.sale_order_ids.filtered('is_subscription').payment_exception = False
        return super()._set_done(**kwargs)

    def _set_pending(self, **kwargs):
        self.sale_order_ids.filtered('is_subscription').payment_exception = False
        return super()._set_pending(**kwargs)

    def _set_authorize(self, **kwargs):
        self.sale_order_ids.filtered('is_subscription').payment_exception = False
        return super()._set_authorize(**kwargs)

    def _set_canceled(self, **kwargs):
        self._handle_unsuccessful_transaction()
        return super()._set_canceled(**kwargs)

    def _set_error(self, state_message):
        self._handle_unsuccessful_transaction()
        return super()._set_error(state_message)

    def _handle_unsuccessful_transaction(self):
        """ Unset pending transactions for subscriptions and cancel their draft invoices. """
        for transaction in self:
            subscriptions = transaction.sale_order_ids.filtered('is_subscription')
            if subscriptions:
                subscriptions.pending_transaction = False
                transaction._cancel_draft_invoices()

    def _cancel_draft_invoices(self):
        """ Cancel draft invoices attached to subscriptions. """
        self.ensure_one()
        subscriptions = self.sale_order_ids.filtered('is_subscription')
        draft_invoices = subscriptions.order_line.invoice_lines.move_id.filtered(lambda am: am.state == 'draft')
        if draft_invoices:
            draft_invoices.state = 'cancel'
