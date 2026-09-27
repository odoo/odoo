# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.delivery.tests.cash_on_delivery_common import CashOnDeliveryCommon


@tagged("post_install", "-at_install")
class TestCODPaymentTransaction(CashOnDeliveryCommon):
    _test_user_groups = None  # FIXME list needed groups

    def test_choosing_cod_payment_confirms_order(self):
        self._disable_post_process_patcher()
        order = self.sale_order
        self._create_cod_transaction()
        with mute_logger("odoo.addons.sale.models.payment_transaction"):
            self._run_post_processing()

        self.assertEqual(order.state, "sale")

    def test_choosing_cod_payment_keeps_the_transaction_pending(self):
        """The customer only commits to pay at checkout; the money is collected on delivery."""
        self._disable_post_process_patcher()
        order = self.sale_order
        tx = self._create_cod_transaction()
        with mute_logger("odoo.addons.sale.models.payment_transaction"):
            self._run_post_processing()

        self.assertEqual(tx.state, "pending")
        self.assertEqual(order.state, "sale")
        self.assertEqual(order.amount_paid, 0, msg="No money has been received yet")
        self.assertEqual(
            order.amount_unpaid,
            order.amount_total,
            msg="The order must remain payable from the Point of Sale",
        )
