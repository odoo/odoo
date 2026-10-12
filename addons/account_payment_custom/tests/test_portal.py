# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.account_payment.controllers.portal import PortalAccount as AccountPaymentPortal
from odoo.addons.account_payment_custom.controllers.portal import Portal
from odoo.addons.account_payment_custom.tests.common import AccountPaymentCustomCommon
from odoo.addons.http_routing.tests.common import MockRequest


@tagged("-at_install", "post_install")
class TestPortal(AccountPaymentCustomCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.invoice = cls._create_invoice(post=True)

    def test_get_common_page_view_values_called_with_is_invoice_from_invoice_page(self):
        with MockRequest(self.env):
            with patch.object(
                AccountPaymentPortal,
                "_get_common_page_view_values",
            ) as mock_get_common_page_view_values:
                Portal()._invoice_get_page_view_values(
                    self.invoice, self.invoice._portal_ensure_token()
                )
                self.assertIn("is_invoice", mock_get_common_page_view_values.call_args.kwargs)

    def test_get_common_page_view_values_called_with_is_invoice_from_overdue_invoices_page(self):
        with MockRequest(self.env):
            with patch.object(
                AccountPaymentPortal,
                "_get_common_page_view_values",
            ) as mock_get_common_page_view_values:
                Portal()._overdue_invoices_get_page_view_values(self.invoice)
                self.assertIn("is_invoice", mock_get_common_page_view_values.call_args.kwargs)
