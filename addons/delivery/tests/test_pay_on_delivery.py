# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.delivery.tests.cash_on_delivery_common import CashOnDeliveryCommon


@tagged('post_install', '-at_install')
class TestPayOnDelivery(CashOnDeliveryCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_line = cls.sale_order.order_line[0]
        cls.product_line.qty_delivered_method = 'manual' # Ensure sale_stock doesn't break the tests
        cls.sale_order.action_confirm()
        cls.product_line.qty_delivered = cls.product_line.product_uom_qty  # Fully delivered
        cls.cod_tx = cls._create_cod_transaction()

    def setUp(self):
        self.enable_post_process_patcher = False
        super().setUp()

    def test_no_confirmation_required_if_nothing_was_delivered(self):
        self.product_line.qty_delivered = 0

        action = self.sale_order.action_open_pay_on_delivery_form()

        self.assertIs(action, True)

    def test_confirmation_required_if_new_quantity_delivered(self):
        self.assertGreater(self.sale_order.amount_on_delivery, 0)

        action = self.sale_order.action_open_pay_on_delivery_form()

        self.assert_dict_almost_equal(
            action, {'type': 'ir.actions.act_window', 'res_model': 'pay.on.delivery'}
        )

    def test_final_action_confirms_payment_on_delivery(self):
        wizard = Form.from_action(
            self.env, self.sale_order.action_open_pay_on_delivery_form()
        ).save()

        with patch.object(self.env.registry['ir.cron'], '_trigger') as mocked_cron_trigger:
            # Simulate a click on the "Confirm Payment" button
            final_action = wizard.action_confirm_next_payment()

        self.assert_dict_almost_equal(
            final_action, {'type': 'ir.actions.client', 'tag': 'display_notification'}
        )
        mocked_cron_trigger.assert_called_once()
        self.cod_tx._post_process()  # Simulate cron trigger
        self.assertRecordValues(self.cod_tx, [{'state': 'done'}])
        self.assertRecordValues(self.cod_tx.payment_id, [{'amount': self.sale_order.amount_total}])

    def test_confirm_orders_sequentialy(self):
        order1, order2 = self.sale_order, self._create_so()
        order2.order_line.qty_delivered_method = 'manual'
        order2.action_confirm()
        cod_txs = self.cod_tx + self._create_cod_transaction(sale_order=order2)
        order2.order_line.qty_delivered = order2.order_line.product_uom_qty  # Both fully delivered

        # Step 1: Open the "Pay on Delivery" form for two orders
        wizard = Form.from_action(
            self.env, (order1 + order2).action_open_pay_on_delivery_form()
        ).save()
        # The form is open, but nothing should be confirmed yet
        self.assertFalse(wizard._get_confirmed_orders())
        self.assertEqual(wizard.next_order_id, order2)  # Uses sale.order default order

        # Step 2: Confirm the payment for the first order
        wizard = Form.from_action(wizard.env, wizard.action_confirm_next_payment()).save()
        self.assertEqual(wizard._get_confirmed_orders(), order2)
        self.assertEqual(wizard.next_order_id, order1)

        # Step 3: Confirm the payment for the second and final order
        with patch.object(self.env.registry['ir.cron'], '_trigger') as mocked_cron_trigger:
            final_action = wizard.action_confirm_next_payment()

        self.assert_dict_almost_equal(
            final_action, {'type': 'ir.actions.client', 'tag': 'display_notification'}
        )
        mocked_cron_trigger.assert_called_once()
        cod_txs._post_process()  # Simulate cron trigger
        self.assertRecordValues(cod_txs, [{'state': 'done'}, {'state': 'done'}])
        self.assertRecordValues(
            cod_txs.payment_id, [{'amount': order1.amount_total}, {'amount': order2.amount_total}]
        )

    def test_confirm_partially_delivered_order(self):
        self.product_line.qty_delivered = 3  # Out of 5
        amount_total = self.sale_order.amount_total
        amount_on_delivery = self.sale_order.amount_on_delivery

        self.sale_order._action_confirm_payment_on_delivery()
        self.cod_tx._post_process()  # Simulate cron trigger

        self.assertRecordValues(self.cod_tx, [{'state': 'cancel'}])
        self.assertRecordValues(self.cod_tx.child_transaction_ids, [
            {'state': 'done', 'amount': amount_on_delivery},
            {'state': 'pending', 'amount': amount_total - amount_on_delivery},
        ])  # fmt: skip

    def test_old_transactions_are_canceled(self):
        new_cod_tx = self._create_cod_transaction()

        self.sale_order._action_confirm_payment_on_delivery()
        (self.cod_tx + new_cod_tx)._post_process()  # Simulate cron trigger

        self.assertRecordValues(self.cod_tx + new_cod_tx, [{'state': 'cancel'}, {'state': 'done'}])

    def test_raises_if_order_total_increased(self):
        self.product_line.update({'product_uom_qty': 10, 'qty_delivered': 10})

        with self.assertRaisesRegex(UserError, "Please consider generating a new payment link."):
            self.sale_order._action_confirm_payment_on_delivery()

    def test_raises_if_order_total_decreased(self):
        self.product_line.update({'qty_delivered': 2, 'product_uom_qty': 2})

        with self.assertRaisesRegex(UserError, "Please consider generating a new payment link."):
            self.sale_order._action_confirm_payment_on_delivery()

    def test_confirm_payment_on_delivery_with_new_transaction_after_order_total_changed(self):
        self.product_line.update({'product_uom_qty': 10, 'qty_delivered': 10})
        with self.assertRaisesRegex(UserError, "Please consider generating a new payment link."):
            self.sale_order._action_confirm_payment_on_delivery()
        new_cod_tx = self._create_cod_transaction()  # Simulate the creation of a new payment link

        self.sale_order._action_confirm_payment_on_delivery()
        (self.cod_tx + new_cod_tx)._post_process()  # Simulate cron trigger

        self.assertRecordValues(self.cod_tx + new_cod_tx, [{'state': 'cancel'}, {'state': 'done'}])

    def test_amount_on_delivery_includes_undeliverable_base_amount(self):
        self.product_line.qty_delivered = 3  # Out of 5

        self.assertAlmostEqual(
            self.sale_order.amount_on_delivery,
            self.sale_order.amount_total - 2 / 5 * self.product_line.price_total,
            msg="Expected to pay the total - undelivered quantities",
        )

    def test_amount_on_delivery_does_not_include_already_paid_products(self):
        self.product_line.qty_delivered = 3  # Out of 5
        self.sale_order._action_confirm_payment_on_delivery()  # First payment

        self.product_line.qty_delivered = 5  # Fully delivered after first payment

        self.assertAlmostEqual(
            self.sale_order.amount_on_delivery,
            2 / 5 * self.product_line.price_total,
            msg="Expected to pay for the remaining quantities only",
        )

    def test_amount_on_delivery_equals_zero_if_nothing_was_delivered(self):
        self.product_line.qty_delivered = 0

        self.assertEqual(self.sale_order.amount_on_delivery, 0)

    def test_amount_on_delivery_equals_zero_if_everything_was_delivered_and_paid_for(self):
        self.sale_order._action_confirm_payment_on_delivery()

        self.assertRecordValues(self.cod_tx, [{'state': 'done'}])
        self.assertEqual(self.sale_order.amount_on_delivery, 0)

    def test_amount_on_delivery_equals_zero_if_order_does_not_use_pay_on_delivery_case_no_tx(self):
        order = self._create_so(state='sale')
        order.order_line.qty_delivered = order.order_line.product_uom_qty

        self.assertEqual(order.amount_on_delivery, 0)

    def test_amount_on_delivery_equals_zero_if_order_does_not_use_pay_on_delivery_case_tx(self):
        order = self._create_so(state='sale')
        self._create_transaction('direct', sale_order_ids=[Command.set(order.ids)])
        order.order_line.qty_delivered = order.order_line.product_uom_qty

        self.assertEqual(order.amount_on_delivery, 0)

    def test_confirm_payment_without_access_to_payment_transactions(self):
        self.sale_order.user_id = self.sale_user
        order = self.sale_order.with_user(self.sale_user)
        self.assertTrue(order.has_access('read'))
        self.assertTrue(order.has_access('write'))
        self.assertFalse(order.has_field_access(order._fields['transaction_ids'], 'read'))
        self.assertFalse(order.has_field_access(order._fields['transaction_ids'], 'write'))

        delivered_tx_sudo = order._action_confirm_payment_on_delivery()  # Assert doesn't raises

        self.assertEqual(self.cod_tx, delivered_tx_sudo)
        self.assertTrue(delivered_tx_sudo.env.is_superuser())
