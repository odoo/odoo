from datetime import timedelta
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import JsonRpcException, tagged
from odoo.tools import mute_logger

from odoo.addons.account_payment_provider.controllers.payment import PaymentPortal
from odoo.addons.account_payment_provider.controllers.portal import PortalAccount
from odoo.addons.account_payment_provider.tests.common import AccountPaymentCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.portal.controllers.portal import CustomerPortal


@tagged("post_install", "-at_install")
class TestFlows(AccountPaymentCommon, PaymentHttpCommon):
    def _prepare_tx_route_values(self, tx_context, **overrides):
        """Build the values passed to the transaction route, from a payment
        context (as returned by _get_portal_pay_context/_get_payment_context),
        with any field overridden or added via **overrides."""
        return {
            "provider_id": self.provider.id,
            "payment_method_id": self.payment_method_id,
            "token_id": None,
            "amount": tx_context.get("amount"),
            "flow": "direct",
            "tokenization_requested": False,
            "landing_route": tx_context["landing_route"],
            **overrides,
        }

    def test_invoice_payment_flow(self):
        """Test that paying an invoice through `/payment/pay` links the transaction to it."""

        # Pay for this invoice (no impact even if amounts do not match)
        route_values = self._prepare_pay_values()
        route_values["invoice_id"] = self.misc_entry.id
        tx_context = self._get_portal_pay_context(**route_values)

        # /invoice/transaction/<id>
        tx_route_values = self._prepare_tx_route_values(
            tx_context, access_token=tx_context["access_token"]
        )
        with mute_logger("odoo.addons.payment.models.payment_transaction"):
            processing_values = self._get_processing_values(
                tx_route=tx_context["transaction_route"], **tx_route_values
            )
        tx_sudo = self._get_tx(processing_values["reference"])
        # The transaction was created by the RPC call, in another environment, so the invoice's
        # cache must be invalidated before reading the link back.
        self.misc_entry.invalidate_recordset(["transaction_ids"])
        self.assertEqual(self.misc_entry.transaction_ids, tx_sudo)

    def test_check_portal_access_token_before_rerouting_flow(self):
        """Test that access to the provided invoice is checked against the portal access token
        before rerouting the payment flow."""
        payment_portal_controller = PaymentPortal()

        with patch.object(CustomerPortal, "_document_check_access") as mock:
            payment_portal_controller._prepare_extra_payment_form_context()
            self.assertEqual(
                mock.call_count,
                0,
                msg="No check should be made when invoice_id is not provided.",
            )

            mock.reset_mock()

            payment_portal_controller._prepare_extra_payment_form_context(
                invoice_id=self.misc_entry.id, access_token="whatever"
            )
            self.assertEqual(
                mock.call_count,
                1,
                msg="The check should be made as invoice_id is provided.",
            )

    def test_check_payment_access_token_before_rerouting_flow(self):
        """Test that access to the provided invoice is checked against the payment access token
        before rerouting the payment flow."""
        payment_portal_controller = PaymentPortal()

        def _document_check_access_mock(*_args, **_kwargs):
            raise AccessError("")

        with (
            patch.object(
                CustomerPortal, "_document_check_access", _document_check_access_mock
            ),
            patch(
                "odoo.addons.payment.utils.is_access_token_valid",
                return_value=False,
            ) as check_payment_access_token_mock,
        ):
            with self.assertRaises(AccessError):
                payment_portal_controller._prepare_extra_payment_form_context(
                    invoice_id=self.misc_entry.id, access_token="whatever"
                )
            self.assertEqual(
                check_payment_access_token_mock.call_count,
                1,
                msg="The access token should be checked again as a payment access token if the"
                " check as a portal access token failed.",
            )

    @mute_logger("odoo.http")
    def test_transaction_route_rejects_unexpected_kwarg(self):
        url = self._build_url(f"/invoice/transaction/{self.misc_entry.id}/")
        route_kwargs = {
            "access_token": self.misc_entry._portal_get_or_create_token(),
            "partner_id": self.partner.id,  # This should be rejected.
        }
        with self.assertRaises(JsonRpcException, msg="odoo.exceptions.ValidationError"):
            self.call_jsonrpc(url, route_kwargs)

    def test_public_user_new_company(self):
        """Test that the payment of an invoice is correctly processed when
        using public user with a new company."""
        self.amount = 1000.0

        invoice = self.init_invoice(
            "out_invoice",
            self.partner,
            amounts=[self.amount],
            currency=self.currency,
        )
        invoice.action_post()
        self.assertEqual(invoice.payment_state, "not_paid")

        route_values = self._prepare_pay_values()
        route_values["invoice_id"] = invoice.id
        tx_context = self._get_portal_pay_context(**route_values)

        tx_route_values = self._prepare_tx_route_values(
            tx_context, access_token=tx_context["access_token"]
        )
        with mute_logger("odoo.addons.payment.models.payment_transaction"):
            processing_values = self._get_processing_values(
                tx_route=tx_context["transaction_route"], **tx_route_values
            )
        tx_sudo = self._get_tx(processing_values["reference"])
        tx_sudo._set_done()

        url = self._build_url("/payment/status/poll")
        resp = self.call_jsonrpc(url, {})
        self.assertTrue(tx_sudo.is_post_processed)

        self.assertEqual(resp["state"], "done")
        self.assertTrue(invoice.payment_state in ("in_payment", "paid"))

    def test_invoice_overdue_payment_flow(self):
        """Test that the overdue payment flow processes an invoice for its full amount."""
        # A dedicated user is needed to authenticate the portal request.
        partner = self.env["res.partner"].create({"name": "Alsh"})
        self.env["res.users"].create(
            {
                "login": "TestUser",
                "password": "Odoo@123",
                "group_ids": [
                    Command.set(self.env.ref("account.group_account_manager").ids)
                ],
                "partner_id": partner.id,
            }
        )
        # The invoice must be past its due date and unpaid to show up as overdue.
        invoice = self.init_invoice(
            "out_invoice",
            partner,
            amounts=[1000.0],
            currency=self.currency,
        )
        invoice.write({"invoice_date_due": invoice.invoice_date - timedelta(days=10)})
        invoice.action_post()
        self.assertEqual(invoice.payment_state, "not_paid")

        # The overdue page redirects to /my for users without read access on invoices.
        self.authenticate("TestUser", "Odoo@123")
        overdue_url = self._build_url("/my/invoices/overdue")
        resp = self._make_http_get_request(overdue_url, {})

        self.assertEqual(resp.status_code, 200)

        tx_context = self._get_payment_context(resp)

        self.assertEqual(tx_context.get("amount"), invoice.amount_total)
        self.assertEqual(tx_context["payment_reference"], invoice.payment_reference)

        tx_route_values = self._prepare_tx_route_values(
            tx_context, payment_reference=tx_context["payment_reference"]
        )
        with mute_logger("odoo.addons.payment.models.payment_transaction"):
            processing_values = self._get_processing_values(
                tx_route=tx_context["transaction_route"], **tx_route_values
            )
        tx_sudo = self._get_tx(processing_values["reference"])
        tx_sudo._set_done()

        self.assertEqual(tx_sudo.amount, invoice.amount_total)

        url = self._build_url("/payment/status/poll")
        resp = self.call_jsonrpc(url, {})
        self.assertTrue(tx_sudo.is_post_processed)

        self.assertEqual(resp["state"], "done")
        self.assertTrue(
            invoice.payment_state == invoice._get_invoice_in_payment_state()
        )

    def test_out_invoice_get_page_view_values(self):
        """Test the invoice-specific portal page view values of an out invoice"""
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.partner,
            amounts=[50.0],
            currency=self.currency,
        )

        def mock_get_page_view_values(
            self, document, access_token, values, *args, **kwargs
        ):
            return values

        with patch.object(
            PortalAccount, "_get_page_view_values", mock_get_page_view_values
        ):
            values = PortalAccount()._invoice_get_page_view_values(
                invoice,
                invoice.access_token,
                amount=26.0,
                payment=True,
            )

        self.assertEqual(values["page_name"], "invoice")
        self.assertEqual(values["invoice"], invoice)
        self.assertEqual(values["amount_paid"], 0.0)
        self.assertEqual(values["amount_due"], 50.0)
        self.assertEqual(values["next_amount_to_pay"], 26.0)
        self.assertEqual(values["payment_state"], "not_paid")
        self.assertTrue(values["payment"])
