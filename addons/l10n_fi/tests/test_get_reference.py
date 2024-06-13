# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class InvoiceGetReferenceTest(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('fi')
    def setUpClass(cls):
        super().setUpClass()

        cls.invoice = cls.init_invoice('out_invoice', products=cls.product_a+cls.product_b)

    def test_get_reference_finnish_invoice(self):
        self.assertFalse(self.invoice.payment_reference)
        self.invoice.journal_id.invoice_reference_model = 'fi'
        self.invoice.action_post()
        self.assertTrue(self.invoice.payment_reference)

    def test_get_reference_finnish_partner(self):
        self.assertFalse(self.invoice.payment_reference)
        self.invoice.journal_id.invoice_reference_type = 'partner'
        self.invoice.journal_id.invoice_reference_model = 'fi'
        self.invoice.action_post()
        self.assertTrue(self.invoice.payment_reference)

    def test_get_reference_finnish_rf_invoice(self):
        self.assertFalse(self.invoice.payment_reference)
        self.invoice.journal_id.invoice_reference_model = 'fi_rf'
        self.invoice.action_post()
        self.assertTrue(self.invoice.payment_reference)

    def test_get_reference_finnish_rf_partner(self):
        self.assertFalse(self.invoice.payment_reference)
        self.invoice.journal_id.invoice_reference_type = 'partner'
        self.invoice.journal_id.invoice_reference_model = 'fi_rf'
        self.invoice.action_post()
        self.assertTrue(self.invoice.payment_reference)
