# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.addons.sale_subscription_external_tax.tests.test_sale_subscription import TestSaleSubscriptionExternalCommon
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestExternalTaxSubscriptionController(TestSaleSubscriptionExternalCommon, PaymentHttpCommon, TestSubscriptionCommon):
    def test_01_external_taxes_called_in_preview(self):
        self.subscription.partner_id = self.user_portal.partner_id
        self.subscription._portal_ensure_token()

        url = "/my/subscriptions/%s?access_token=%s" % (self.subscription.id, self.subscription.access_token)
        with patch('odoo.addons.sale_external_tax.models.sale_order.SaleOrder._set_external_taxes', autospec=True) as mocked_set, \
             self.patch_set_external_taxes():
            self.url_open(url, allow_redirects=False)

        self.assertIn(
            self.subscription,
            [args[0] for args, kwargs in mocked_set.call_args_list],
            'Should have queried external taxes on the subscription.'
        )

    def test_02_external_taxes_called_in_manual_payment(self):
        with self.patch_set_external_taxes():
            self.subscription.action_confirm()
        self.subscription._portal_ensure_token()
        self.assertEqual(
            len(self.subscription.invoice_ids), 0, "There should be no invoices yet."
        )

        url = self._build_url("/my/subscriptions/%s/transaction/" % self.subscription.id)
        data = {
            "access_token": self.subscription.access_token,
            "landing_route": self.subscription.get_portal_url(),
            "provider_id": self.dummy_provider.id,
            "payment_method_id": self.payment_method_id,
            "token_id": False,
            "flow": "direct",
        }

        with self.patch_set_external_taxes() as mocked_set:
            self.make_jsonrpc_request(url, data)

        self.assertEqual(
            len(self.subscription.invoice_ids), 1, "One invoice should have been created."
        )
        self.assertEqual(
            [self.subscription.invoice_ids[0]],
            [args[0] for args, kwargs in mocked_set.call_args_list],
            "Should have queried avatax on the created invoice when manually initiating a payment.",
        )
