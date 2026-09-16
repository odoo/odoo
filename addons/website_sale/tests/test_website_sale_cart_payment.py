from unittest.mock import patch

from odoo.fields import Command
from odoo.tests.common import JsonRpcException, tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged("post_install", "-at_install")
class WebsiteSaleCartPayment(PaymentHttpCommon, WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tx = cls.env["payment.transaction"].create(
            {
                "payment_method_id": cls.payment_method_id,
                "amount": cls.amount,
                "currency_id": cls.currency.id,
                "provider_id": cls.provider.id,
                "reference": cls.reference,
                "operation": "online_redirect",
                "partner_id": cls.partner.id,
            }
        )
        cls.cart.write({"transaction_ids": [Command.set([cls.tx.id])]})

    def test_unpaid_orders_can_be_retrieved(self):
        for unpaid_order_tx_state in ("draft", "cancel", "error"):
            self.tx.state = unpaid_order_tx_state
            with MockRequest(
                self.env, website=self.website, sale_order_id=self.cart.id
            ) as request:
                self.assertEqual(
                    request.cart,
                    self.cart,
                    msg=f"The transaction state '{unpaid_order_tx_state}' should not prevent "
                    f"retrieving the linked order.",
                )

    def test_paid_orders_cannot_be_retrieved(self):
        self.tx.provider_id.support_manual_capture = "full_only"
        for paid_order_tx_state in ("pending", "authorized", "done"):
            self.tx.state = paid_order_tx_state
            with MockRequest(
                self.env, website=self.website, sale_order_id=self.cart.id
            ) as request:
                self.assertFalse(
                    request.cart,
                    msg=f"The transaction state '{paid_order_tx_state}' should prevent retrieving "
                    f"the linked order.",
                )

    @mute_logger("odoo.http")
    def test_transaction_route_rejects_unexpected_kwarg(self):
        url = self._build_url(f"/shop/payment/transaction/{self.cart.id}")
        route_kwargs = {
            "access_token": self.cart._portal_get_or_create_token(),
            "partner_id": self.partner.id,
        }
        with self.assertRaises(JsonRpcException, msg="odoo.exceptions.ValidationError"):
            self.call_jsonrpc(url, route_kwargs)

    def test_payment_confirmation_mail(self):
        salesperson = self.env.ref("base.user_admin")
        self.website.salesperson_id = salesperson
        self.cart.user_id = False
        self.tx._set_pending()
        with patch.object(
            self.env.registry["sale.order"], "_send_mail_order_notification"
        ) as mock:
            self.tx._post_process()
            self.assertEqual(
                mock.call_count, 1, "One payment confirmation mail should be sent"
            )
            self.assertEqual(
                self.cart.user_id,
                salesperson,
                "Salesperson should get assigned when sending payment confirmation mail",
            )
