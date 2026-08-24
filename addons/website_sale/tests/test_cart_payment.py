# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.fields import Command
from odoo.tests.common import JsonRpcException, tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.website_sale.controllers.cart import Cart
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class WebsiteSaleCartPayment(PaymentHttpCommon, WebsiteSaleCommon):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tx = cls.env["payment.transaction"].create({
            "payment_method_id": cls.payment_method_id,
            "amount": cls.amount,
            "currency_id": cls.currency.id,
            "provider_id": cls.provider.id,
            "reference": cls.reference,
            "operation": "online_redirect",
            "partner_id": cls.cart.partner_id.id,
        })
        cls.cart.write({"transaction_ids": [Command.set([cls.tx.id])]})

    def test_unpaid_orders_can_be_retrieved(self):
        """Test that fetching sales orders linked to a payment transaction in the states 'draft',
        'cancel', or 'error' returns the orders.
        """
        for unpaid_order_tx_state in ("draft", "cancel", "error"):
            self._update_transaction(self.tx, state=unpaid_order_tx_state)
            with self.mock_request(sale_order_id=self.cart.id) as request:
                self.assertEqual(
                    request.cart,
                    self.cart,
                    msg=f"The transaction state '{unpaid_order_tx_state}' should not prevent "
                    f"retrieving the linked order.",
                )

    def test_paid_orders_cannot_be_retrieved(self):
        """Test that fetching sales orders linked to a payment transaction in the states 'pending',
        'authorized', or 'done' returns an empty recordset to prevent updating the paid orders.
        """
        self.tx.provider_id.support_manual_capture = "full_only"
        for paid_order_tx_state in ("pending", "authorized", "done"):
            self._update_transaction(self.tx, state=paid_order_tx_state)
            with self.mock_request(sale_order_id=self.cart.id) as request:
                self.assertFalse(
                    request.cart,
                    msg=f"The transaction state '{paid_order_tx_state}' should prevent retrieving "
                    f"the linked order.",
                )

    @mute_logger("odoo.http")
    def test_transaction_route_rejects_unexpected_kwarg(self):
        self.cart.partner_id.write(self.dummy_partner_address_values.copy())
        self.cart._set_delivery_method(self.free_delivery)
        url = self._build_url(f"/shop/payment/transaction/{self.cart.id}")
        route_kwargs = {
            "access_token": self.cart._portal_ensure_token(),
            "partner_id": self.partner.id,  # This should be rejected.
        }
        with self.assertRaises(JsonRpcException, msg="odoo.exceptions.ValidationError"):
            self.make_jsonrpc_request(url, route_kwargs)

    def test_payment_confirmation_mail(self):
        """Check that a salesperson gets assigned when sending payment confirmation mails."""
        salesperson = self.env.ref("base.user_admin")
        self.website.salesperson_id = salesperson
        self.cart.user_id = False
        self._update_transaction(self.tx, state="pending")
        with patch.object(self.env.registry["sale.order"], "_send_order_notification_mail") as mock:
            self._run_post_processing(self.tx)
            self.assertEqual(mock.call_count, 1, "One payment confirmation mail should be sent")
            self.assertEqual(
                self.cart.user_id,
                salesperson,
                "Salesperson should get assigned when sending payment confirmation mail",
            )

    def _create_abandoned_order_with_transaction(self, tx_state):
        order = self.env["sale.order"].create({
            "partner_id": self.portal_user.partner_id.id,
            "website_id": self.website.id,
            "state": "draft",
            "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1})],
        })
        tx = self._create_transaction(
            flow="redirect",
            state=tx_state,
            partner_id=order.partner_id.id,
            reference=f"Test Transaction - abandoned - {order.id}",
        )
        order.transaction_ids = [Command.set([tx.id])]
        return order

    def test_abandoned_cart_not_resurrected_implicitly_when_transaction_ongoing(self):
        """`_get_and_cache_current_cart` must not silently resurrect a draft order as the
        active cart when its latest transaction is pending, authorized, or done - even if
        the session cart key was cleared (e.g. by `sale_reset()` after a redirect payment
        race condition).
        """
        abandoned_order = self._create_abandoned_order_with_transaction("done")
        with self.mock_request(user=self.portal_user) as request:
            self.assertFalse(request.session.get("sale_order_id"))
            cart = request.cart
            self.assertNotEqual(cart, abandoned_order)

    def test_abandoned_cart_not_cancelled_via_recovery_link_when_transaction_ongoing(self):
        """The `/shop/cart` recovery-link flow (`id` + `access_token`) must not silently
        merge and cancel a draft order whose latest transaction is pending, authorized, or
        done, even if a different order is currently active in the session.
        """
        abandoned_order = self._create_abandoned_order_with_transaction("done")
        access_token = abandoned_order._portal_ensure_token()
        # A different order is already the active session cart.
        active_order = self.env["sale.order"].create({
            "partner_id": self.portal_user.partner_id.id,
            "website_id": self.website.id,
            "state": "draft",
        })
        with self.mock_request(
            user=self.portal_user, path="/shop/cart", sale_order_id=active_order.id
        ):
            Cart().cart(id=abandoned_order.id, access_token=access_token)
        self.assertEqual(abandoned_order.state, "draft")
