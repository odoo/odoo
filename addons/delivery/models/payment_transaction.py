# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError
from odoo.fields import Command, Domain


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process(self):
        """ Override of `payment` to confirm orders with the cash_on_delivery payment method and
        trigger a picking creation. """
        cod_pending_txs = self.filtered(
            lambda tx: tx.provider_id.custom_mode == 'cash_on_delivery' and tx.state == 'pending'
        )
        cod_pending_txs.sale_order_ids.filtered(
            lambda so: so.state == 'draft'
        ).with_context(send_email=True).action_confirm()
        super()._post_process()

    def _filtered_pay_on_delivery(self):
        return self.filtered_domain(self._get_pay_on_delivery_transaction_domain())

    def _get_pay_on_delivery_transaction_domain(self):
        pms_on_delivery = self.env['payment.method']._get_payment_method_on_delivery_codes()
        return Domain([
            ('payment_method_id.code', 'in', pms_on_delivery),
            ('state', '=', 'pending'),
        ])

    def _confirm_payment_on_delivery_and_post_process(self):
        """Confirm transactions created using a "Pay on Delivery" payment method, and trigger the
        post process cron.

        If the order's `amount_on_delivery` to be collected is lower than the remaining balance,
        the last transaction is split into two new transactions: 1. to confirm the
        `amount_on_delivery`, and 2. to follow the remaining balance.

        :raises UserError: If the latest transaction is outdated.
        :return: The confirmed transaction(s). May include newly created transactions.
        :rtype: payment.transaction
        """
        delivered_txs, followup_txs = self.browse(), self.browse()
        for order, pending_delivery_txs in (
            self._filtered_pay_on_delivery().grouped('sale_order_ids').items()
        ):
            order.ensure_one()
            last_tx = pending_delivery_txs._get_last()
            remaining_balance = order.amount_total - order.amount_paid

            # Ensure the last transaction is not outdated.
            assert order.currency_id == last_tx.currency_id
            if order.currency_id.compare_amounts(remaining_balance, last_tx.amount):
                raise UserError(
                    self.env._(
                        "The amount authorized by the customer does not match the remaining"
                        " balance of the order. Please consider generating a new payment link."
                        "\n\n- Remaining Balance (%(order)s): %(remaining_balance)s"
                        "\n- Authorized Amount (%(tx)s): %(tx_amount)s",
                        order=order.display_name,
                        remaining_balance=order.currency_id.format(remaining_balance),
                        tx=last_tx.display_name,
                        tx_amount=order.currency_id.format(last_tx.amount),
                    )
                )

            # Cancel all the other pending transactions linked to the same SO.
            if old_txs := pending_delivery_txs - last_tx:
                old_txs._set_canceled_in_favor_of(last_tx)

            delivered_tx, followup_tx = last_tx._compare_with_delivery_amount_or_split()
            delivered_txs |= delivered_tx
            followup_txs |= followup_tx

        delivered_txs._set_done()
        followup_txs._set_pending()
        # The transactions are now done but it didn't automatically trigger a recomputation.
        delivered_txs.sale_order_ids.invalidate_recordset(('amount_on_delivery',), flush=False)
        if delivered_txs:
            self.env.ref('payment.cron_post_process_payment_tx')._trigger()

        return delivered_txs

    def _compare_with_delivery_amount_or_split(self):
        """Compare the `amount_on_delivery` of the transaction's order and split if is lower than
        the transaction's amount.

        :return: A tuple of the delivered/confirmed transaction, a followup transaction if splitted.
        :rtype: tuple[payment.transaction, payment.transaction]
        """
        self.ensure_one()
        order = self.sale_order_ids.ensure_one()
        assert order.currency_id == self.currency_id
        Tx = self.env['payment.transaction']

        cmp = self.currency_id.compare_amounts(order.amount_on_delivery, self.amount)
        if not cmp:  # order.amount_on_delivery == self.amount
            return self, Tx
        if cmp > 0:  # order.amount_on_delivery > self.amount (shouldn't be possible)
            raise UserError(
                self.env._(
                    "The collected amount cannot exceed the authorized amount."
                    " Please contact Odoo support or generate a new payment link."
                )
            )

        # The order was not entirely delivered. Split the transaction in two.
        delivered_tx, followup_tx = Tx.create(self._get_splitted_delivery_transaction_vals())
        self._set_canceled_in_favor_of(delivered_tx + followup_tx)

        return delivered_tx, followup_tx

    def _get_splitted_delivery_transaction_vals(self):
        self.ensure_one()
        order = self.sale_order_ids.ensure_one()
        source_tx = self.source_transaction_id or self
        base_vals = self.copy_data({
            'source_transaction_id': source_tx.id,
            'sale_order_ids': [Command.set(order.ids)],
        })[0]

        def compute_reference(idx_):
            return f"{source_tx.reference}-{len(source_tx.child_transaction_ids) + idx_}"

        return [
            {**base_vals, 'amount': order.amount_on_delivery, 'reference': compute_reference(1)},
            {
                **base_vals,
                'amount': self.amount - order.amount_on_delivery,
                'reference': compute_reference(2),
            },
        ]

    def _set_canceled_in_favor_of(self, favored_txs):
        self._set_canceled(
            state_message=self.env._(
                "Canceled in favor of %(favored_txs)s.",
                favored_txs=", ".join(favored_txs.mapped('display_name')),
            )
        )
