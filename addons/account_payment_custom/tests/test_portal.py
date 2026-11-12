# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import JsonRpcException, tagged
from odoo.tools import mute_logger

from odoo.addons.account_payment_custom.controllers.portal import Portal
from odoo.addons.account_payment_custom.tests.common import AccountPaymentCustomCommon
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.payment.tests.http_common import PaymentHttpCommon


@tagged("-at_install", "post_install")
class TestPortal(AccountPaymentCustomCommon, PaymentHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.invoice = cls._create_invoice(post=True)

    def test_invoice_page_hides_pay_on_invoice_provider(self):
        with MockRequest(self.env):
            values = Portal()._invoice_get_page_view_values(
                self.invoice, self.invoice._portal_ensure_token()
            )
        self.assertNotIn(self.pay_on_invoice_provider, values["providers_sudo"])

    def test_overdue_invoices_page_hides_pay_on_invoice_provider(self):
        with MockRequest(self.env):
            values = Portal()._overdue_invoices_get_page_view_values(self.invoice)
        self.assertNotIn(self.pay_on_invoice_provider, values["providers_sudo"])

    def _get_payment_link_pm_ids(self, **route_kwargs):
        # Make the provider available outside of invoices, so that only `invoice_id` excludes it
        self.pay_on_invoice_provider.is_published = True
        self.pay_on_invoice_provider.payment_method_ids.active = True
        route_values = self._prepare_pay_values(
            amount=self.invoice.amount_total,
            currency=self.invoice.currency_id,
            partner=self.invoice.partner_id,
        )
        route_values["company_id"] = self.invoice.company_id.id
        return self._get_portal_pay_context(**route_values, **route_kwargs)["payment_method_ids"]

    def test_payment_link_shows_pay_on_invoice_provider_without_invoice(self):
        pm_ids = self._get_payment_link_pm_ids()
        self.assertIn(self.pay_on_invoice_provider.payment_method_ids[:1].id, pm_ids)

    def test_payment_link_of_invoice_hides_pay_on_invoice_provider(self):
        pm_ids = self._get_payment_link_pm_ids(invoice_id=self.invoice.id)
        self.assertNotIn(self.pay_on_invoice_provider.payment_method_ids[:1].id, pm_ids)

    @mute_logger("odoo.http")
    def test_invoice_transaction_rejects_pay_on_invoice_provider(self):
        # Make the provider available outside of invoices, so that only `is_invoice` excludes it
        self.pay_on_invoice_provider.is_published = True
        self.pay_on_invoice_provider.payment_method_ids.active = True
        route_values = self._prepare_transaction_values(
            self.pay_on_invoice_provider.payment_method_ids[:1].id, None, "direct"
        )
        route_values["provider_id"] = self.pay_on_invoice_provider.id
        for key in ("currency_id", "partner_id", "reference_prefix"):
            route_values.pop(key)  # The route takes these values from the invoice
        route_values["access_token"] = self.invoice._portal_ensure_token()
        with self.assertRaisesRegex(JsonRpcException, "ValidationError"):
            self._portal_transaction(
                tx_route=f"/invoice/transaction/{self.invoice.id}", **route_values
            )
