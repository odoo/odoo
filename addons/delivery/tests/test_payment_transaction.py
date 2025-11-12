# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.delivery.tests.cash_on_delivery_common import CashOnDeliveryCommon


@tagged("post_install", "-at_install")
class TestCODPaymentTransaction(CashOnDeliveryCommon):
    _test_user_groups = None  # FIXME list needed groups

    def test_choosing_cod_payment_confirms_order(self):
        order = self.sale_order
        tx = self._create_cod_transaction()
        with mute_logger("odoo.addons.sale.models.payment_transaction"):
            self._run_post_processing(tx)

        self.assertEqual(order.state, "sale")

    def test_choosing_cod_payment_keeps_the_transaction_pending(self):
        """The customer only commits to pay at checkout; the money is collected on delivery."""
        order = self.sale_order
        tx = self._create_cod_transaction()
        with mute_logger("odoo.addons.sale.models.payment_transaction"):
            self._run_post_processing(tx)

        self.assertEqual(tx.state, "pending")
        self.assertTrue(tx._is_paid(), msg="A pending COD transaction behaves as paid")
        self.assertEqual(order.amount_paid, 0, msg="No money has been received yet")
        self.assertEqual(order.amount_secured, order.amount_total)

    def test_choosing_cod_payment_defers_the_automatic_invoicing(self):
        """No invoice is issued at checkout, so the order keeps an outstanding balance and stays
        visible to the Point of Sale."""
        self.env.company.sudo().sale_automatic_invoice = True
        order = self.sale_order
        tx = self._create_cod_transaction()

        with mute_logger("odoo.addons.sale.models.payment_transaction"):
            self._run_post_processing(tx)

        self.assertFalse(tx.sudo().invoice_ids, msg="The invoicing should be deferred")
        self.assertFalse(order.invoice_ids, msg="The invoicing should be deferred")
        self.assertEqual(
            order.amount_unpaid,
            order.amount_total,
            msg="The order must remain settleable from the Point of Sale",
        )
