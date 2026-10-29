# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest import SkipTest
from urllib.parse import urlsplit

from lxml import html

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.website_sale.controllers.main import WebsiteSale as CheckoutController
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon

# The scenarios of the payment status matrix. Each test below is one call site (a column of the
# matrix) and gives the value that the call site must show for each scenario (a row).
# `None` means that the call site does not apply to the scenario.
SCENARIOS = (
    "split_done_and_authorized",
    "partial_authorized",
    "failed_retry_after_success",
    "cash_on_delivery_pending",
    "wire_transfer_pending",
    "zero_amount",
    "refund",
    "cancelled",
    "split_done_and_pending",
)


@tagged("post_install", "-at_install")
class TestPaymentStatusMatrix(WebsiteSaleCommon, PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.env["ir.module.module"]._get("payment_demo").state != "installed":
            msg = "The payment status matrix needs `payment_demo`"
            raise SkipTest(msg)

        cls.demo_provider = cls._prepare_provider(code="demo")
        ProviderSudo = cls.env["payment.provider"].sudo()
        cls.wire_provider = ProviderSudo.search(
            [("code", "=", "custom"), ("custom_mode", "=", "wire_transfer")], limit=1
        )
        cls.cod_provider = ProviderSudo.search(
            [("code", "=", "custom"), ("custom_mode", "=", "cash_on_delivery")], limit=1
        )
        cls.is_collect_installed = (
            cls.env["ir.module.module"]._get("website_sale_collect").state == "installed"
        )

    # === SCENARIOS === #

    def _build_scenario(self, scenario):
        """Create an order in the given scenario, owned by a new portal customer.

        :param str scenario: The scenario, one of `SCENARIOS`.
        :return: The order, the transaction that the customer has just made (the one monitored in
                 their session), and the customer.
        :rtype: tuple(sale.order, payment.transaction, res.users)
        """
        user = self._create_new_portal_user(login=f"matrix_{scenario}")
        price_unit = 0.0 if scenario == "zero_amount" else 100.0
        order = self._create_so(
            partner_id=user.partner_id.id,
            order_line=[Command.create({"product_id": self.product.id, "price_unit": price_unit})],
        )
        total = order.amount_total
        half = order.currency_id.round(total / 2)

        feedback_tx = self.env["payment.transaction"]
        if scenario == "split_done_and_authorized":
            self._pay(order, half, "authorized")
            feedback_tx = self._pay(order, total - half, "done")
        elif scenario == "partial_authorized":
            feedback_tx = self._pay(order, half, "authorized")
        elif scenario == "failed_retry_after_success":
            self._pay(order, total, "done")
            feedback_tx = self._pay(order, total, "error")
        elif scenario == "cash_on_delivery_pending":
            feedback_tx = self._pay(order, total, "pending", provider=self.cod_provider)
            order.action_confirm()  # As the post-processing of `delivery` does
        elif scenario == "wire_transfer_pending":
            feedback_tx = self._pay(order, total, "pending", provider=self.wire_provider)
            order.state = "sent"  # As the post-processing of `sale` does
        elif scenario == "refund":
            feedback_tx = self._pay(order, total, "done")
            refund_tx = feedback_tx._create_child_transaction(total, is_refund=True)
            self._update_transaction(refund_tx, state="done")
        elif scenario == "cancelled":
            feedback_tx = self._pay(order, half, "done")
            order.state = "cancel"
        elif scenario == "split_done_and_pending":
            self._pay(order, half, "done")
            feedback_tx = self._pay(order, total - half, "pending", provider=self.wire_provider)
        return order, feedback_tx, user

    def _pay(self, order, amount, state, provider=None):
        provider = (provider or self.demo_provider).sudo()
        return self._create_transaction(
            "direct",
            provider_id=provider.id,
            payment_method_id=provider.with_context(active_test=False).payment_method_ids[:1].id,
            sale_order_ids=[Command.set(order.ids)],
            partner_id=order.partner_id.id,
            currency_id=order.currency_id.id,
            amount=amount,
            state=state,
            reference=f"{order.name}-{len(order.transaction_ids)}",
        )

    def _check_matrix_column(self, expected_by_scenario, get_value):
        for scenario in SCENARIOS:
            expected = expected_by_scenario[scenario]  # A KeyError means a scenario is missing
            if expected is None:
                continue
            with self.subTest(scenario=scenario):
                order, feedback_tx, user = self._build_scenario(scenario)
                self.assertEqual(get_value(order, feedback_tx, user), expected)

    # === DOCUMENT STATUS === #

    def test_order_payment_status_considers_all_transactions(self):
        self._check_matrix_column(
            {
                # The vocabulary resolves settled amounts first, so half done and half authorized
                # is `partial`. `_is_paid()` considers the same order fully paid.
                "split_done_and_authorized": "partial",
                "partial_authorized": "authorized",
                "failed_retry_after_success": "paid",
                "cash_on_delivery_pending": "pending",
                "wire_transfer_pending": "pending",
                "zero_amount": "paid",
                "refund": "paid",  # The refund transaction is not linked to the order
                "cancelled": "partial",  # The status ignores the order's own state
                "split_done_and_pending": "partial",
            },
            lambda order, _tx, _user: order._get_payment_status(),
        )

    def test_order_confirmation_subject_never_says_pending(self):
        template = self.env.ref("sale.mail_template_sale_confirmation")
        self._check_matrix_column(
            dict.fromkeys(SCENARIOS, False),
            lambda order, _tx, _user: (
                "Pending" in template._render_field("subject", order.ids)[order.id]
            ),
        )

    # === YES/NO CHECKS === #

    def test_payment_started_ignores_failed_retries(self):
        self._check_matrix_column(
            {
                "split_done_and_authorized": True,
                "partial_authorized": True,
                "failed_retry_after_success": True,
                "cash_on_delivery_pending": True,
                "wire_transfer_pending": True,
                "zero_amount": False,
                "refund": True,
                "cancelled": True,
                "split_done_and_pending": True,
            },
            lambda order, _tx, _user: order._is_payment_started(),
        )

    def test_session_cart_is_kept_only_until_payment_unless_partially_paid(self):
        def is_cart_kept(order, _tx, user):
            with self.mock_request(user=user, sale_order_id=order.id) as request:
                return request.cart == order

        self._check_matrix_column(
            {
                "split_done_and_authorized": False,
                "partial_authorized": True,
                "failed_retry_after_success": False,
                "cash_on_delivery_pending": False,
                "wire_transfer_pending": False,
                "zero_amount": True,
                "refund": False,
                "cancelled": False,
                "split_done_and_pending": True,
            },
            is_cart_kept,
        )

    def test_abandoned_cart_is_revived_only_without_payment(self):
        def is_cart_revived(order, _tx, user):
            with self.mock_request(user=user) as request:
                return request.cart == order

        self._check_matrix_column(
            {
                "split_done_and_authorized": False,
                "partial_authorized": False,
                "failed_retry_after_success": False,
                "cash_on_delivery_pending": False,
                "wire_transfer_pending": False,
                "zero_amount": True,
                "refund": False,
                "cancelled": False,
                "split_done_and_pending": False,
            },
            is_cart_revived,
        )

    def test_payment_validation_without_monitored_transaction_redirects_on_order_payments(self):
        """The session can lose the monitored transaction (e.g., the customer returns from the
        provider in another browser). The validation then decides from the order's payments."""

        def get_redirect(order, _tx, user):
            with self.mock_request(
                user=user, path="/shop/payment/validate", sale_order_id=order.id
            ) as request:
                request.session["sale_last_order_id"] = order.id
                return urlsplit(CheckoutController().shop_payment_validate().location).path

        self._check_matrix_column(
            {
                "split_done_and_authorized": "/shop/confirmation",
                "partial_authorized": "/shop/payment",
                "failed_retry_after_success": "/shop/confirmation",
                "cash_on_delivery_pending": "/shop/confirmation",
                "wire_transfer_pending": "/shop/confirmation",
                "zero_amount": None,  # Goes through the checkout steps instead
                "refund": "/shop/confirmation",
                "cancelled": "/shop/confirmation",
                "split_done_and_pending": "/shop/payment",
            },
            get_redirect,
        )

    # === DIRECT FEEDBACK === #

    def test_confirmation_banner_describes_the_monitored_transaction(self):
        def get_banner_alert(order, feedback_tx, user):
            with self.mock_request(user=user):
                rendered = self.env["ir.qweb"]._render(
                    "website_sale.payment_confirmation_status",
                    {
                        "order": order.sudo(),
                        "feedback_tx_sudo": feedback_tx.sudo(),
                        "order_tracking_info": {},
                    },
                )
            banners = html.fromstring(str(rendered)).xpath("//*[@id='order_confirmation_banner']")
            if not banners:
                return "no banner"
            classes = banners[0].get("class", "").split()
            return next((cls for cls in classes if cls.startswith("alert-")), "instructions")

        self._check_matrix_column(
            {
                "split_done_and_authorized": "alert-success",
                "partial_authorized": "alert-warning",
                "failed_retry_after_success": "alert-danger",
                # `delivery` marks it as a success on the portal, but the confirmation page only
                # does with `website_sale_collect`
                "cash_on_delivery_pending": (
                    "alert-success" if self.is_collect_installed else "alert-info"
                ),
                "wire_transfer_pending": "instructions",
                "zero_amount": "no banner",
                "refund": "alert-success",
                "cancelled": "alert-warning",
                "split_done_and_pending": "instructions",
            },
            get_banner_alert,
        )

    def test_payment_receipt_subject_follows_the_notified_transaction(self):
        template = self.env.ref("sale.mail_template_sale_payment_executed")
        self._check_matrix_column(
            {
                "split_done_and_authorized": False,
                "partial_authorized": False,
                "failed_retry_after_success": False,
                "cash_on_delivery_pending": True,
                "wire_transfer_pending": True,
                "zero_amount": False,
                "refund": False,
                "cancelled": False,
                "split_done_and_pending": True,
            },
            lambda order, _tx, _user: (
                "Pending Order" in template._render_field("subject", order.ids)[order.id]
            ),
        )
