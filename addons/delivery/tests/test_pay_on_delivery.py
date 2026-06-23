# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import RecordCapturer, tagged

from odoo.addons.delivery.tests.cash_on_delivery_common import CashOnDeliveryCommon


@tagged("post_install", "-at_install")
class TestPayOnDelivery(CashOnDeliveryCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_line = cls.sale_order.order_line[0]
        cls.sale_order.order_line = [Command.create({"product_id": cls.service_product.id})]
        cls.cod_tx = cls._create_cod_transaction()
        cls.sale_order.action_confirm()
        cls.sale_order.deliver_sold_quantity()  # Fully delivered

        # Freely change the ordered/delivered quantity when sale_stock is installed
        cls.startClassPatcher(
            patch.object(cls.registry["sale.order.line"], "_update_line_quantity")
        )

    @classmethod
    def _create_so(cls, **values):
        # Ensure sale_stock doesn't break the tests
        so = super()._create_so(**values)
        so.order_line.filtered(
            lambda line: line.product_id.type == "consu"
        ).qty_delivered_method = "manual"
        return so

    def setUp(self):
        self.enable_post_process_patcher = False
        self.mock_cron_trigger = self.startPatcher(
            patch.object(self.env.registry["ir.cron"], "_trigger")
        )
        super().setUp()

    def test_confirm_fully_delivered_order(self):
        """A fully delivered order should not create a followup transaction."""
        with RecordCapturer(self.env["payment.transaction"], []) as capture:
            delivered_tx = self.sale_order._confirm_payment_on_delivery()

        self.assertEqual(self.cod_tx, delivered_tx)
        self.assertEqual(self.cod_tx.state, "done")
        self.assertFalse(capture.records, msg="No followup transaction should be created")

    def test_confirm_partially_delivered_order(self):
        """
        The COD transaction should be splitted in two: one including the partially delivered
        quantity amount, and a second to followup on the remaining amount.
        """
        self.product_line.qty_delivered = 3  # Out of 5
        amount_total = self.sale_order.amount_total
        amount_on_delivery = self.sale_order.amount_on_delivery

        self.sale_order._confirm_payment_on_delivery()

        self.assertEqual(self.cod_tx.state, "cancel", msg="Canceled in favor of its children")
        self.assertRecordValues(self.cod_tx.child_transaction_ids, [
            {"state": "done", "amount": amount_on_delivery},
            {"state": "done", "amount": amount_total - amount_on_delivery},
        ])  # fmt: skip

    def test_confirm_order_with_decreased_total(self):
        """
        If the order total decreases after the COD transaction is created, only the new total should
        be confirmed.
        """
        old_total = self.sale_order.amount_total
        self.product_line.write({"product_uom_qty": 3, "qty_delivered": 3})

        delivered_tx = self.sale_order._confirm_payment_on_delivery()

        self.assertRecordValues(self.cod_tx + delivered_tx, [
            # A new transaction should be created for the new (decreased) total
            {"state": "cancel", "amount": old_total},
            {"state": "done", "amount": self.sale_order.amount_total},
        ])  # fmt: skip

    def test_confirm_order_with_increased_total(self):
        """
        If the order total increases beyond the transaction amount, require creating a new
        transaction so the customer explicitly authorizes the higher amount.
        """
        self.product_line.write({"product_uom_qty": 10, "qty_delivered": 10})

        with self.assertRaisesRegex(UserError, "Please consider generating a new payment link."):
            self.sale_order._confirm_payment_on_delivery()

    def test_old_transactions_are_canceled(self):
        """
        If a new COD transaction is created (e.g., because the order total increased), we should
        treat the last transaction as the source of truth, and cancel the old ones.
        """
        new_cod_tx = self._create_cod_transaction()

        delivered_tx = self.sale_order._confirm_payment_on_delivery()

        self.assertEqual(new_cod_tx, delivered_tx, msg="The new transaction should be confirmed")
        self.assertEqual(self.cod_tx.state, "cancel", msg="The old transaction should be canceled")

    def test_confirm_payment_without_access_to_payment_transactions(self):
        self.sale_order.user_id = self.sale_user
        order = self.sale_order.with_user(self.sale_user)
        self.assertTrue(order.has_access("read"))
        self.assertTrue(order.has_access("write"))
        self.assertFalse(order.has_field_access(order._fields["transaction_ids"], "read"))
        self.assertFalse(order.has_field_access(order._fields["transaction_ids"], "write"))

        delivered_tx_sudo = order._confirm_payment_on_delivery()  # Assert doesn't raises

        self.assertEqual(self.cod_tx, delivered_tx_sudo)
        self.assertTrue(delivered_tx_sudo.env.is_superuser())

    def test_amount_on_delivery_includes_undeliverable_base_amount(self):
        self.product_line.qty_delivered = 3  # Out of 5

        self.assertEqual(
            self.sale_order.amount_on_delivery,
            self.sale_order.amount_total - 2 / 5 * self.product_line.price_total,
            msg="Expected to pay the total (service included) minus undelivered quantities",
        )

    def test_amount_on_delivery_does_not_include_already_paid_products(self):
        self.product_line.qty_delivered = 3  # Out of 5
        self.sale_order._confirm_payment_on_delivery()  # First payment

        self.product_line.qty_delivered = 5  # Fully delivered after first payment

        self.assertEqual(
            self.sale_order.amount_on_delivery,
            2 / 5 * self.product_line.price_total,
            msg="Expected to pay for the remaining quantities only",
        )

    def test_amount_on_delivery_equals_zero_if_nothing_was_delivered(self):
        self.product_line.qty_delivered = 0

        self.assertEqual(self.sale_order.amount_on_delivery, 0)

    def test_amount_on_delivery_equals_zero_if_everything_was_delivered_and_paid_for(self):
        self.sale_order._confirm_payment_on_delivery()

        self.assertEqual(self.sale_order.amount_on_delivery, 0)

    def test_amount_on_delivery_equals_zero_if_order_does_not_use_pay_on_delivery(self):
        order = self._create_so(state="sale")
        self._create_transaction("direct", sale_order_ids=[Command.set(order.ids)])
        order.deliver_sold_quantity()

        self.assertEqual(order.amount_on_delivery, 0)

    def test_amount_on_delivery_does_not_include_posted_downpayments(self):
        downpayment_wizard = self.env["sale.advance.payment.inv"].create({
            "sale_order_ids": [Command.set(self.sale_order.ids)],
            "advance_payment_method": "percentage",
            "amount": 20,
        })

        downpayment_wizard._create_invoices(self.sale_order).action_post()
        downpayment_wizard._create_invoices(self.sale_order).button_cancel()
        downpayment_wizard._create_invoices(self.sale_order)  # Keep in draft

        self.assertEqual(
            self.sale_order.amount_on_delivery,
            0.8 * self.sale_order.amount_total,
            msg="Posted downpayment should not be included",
        )
