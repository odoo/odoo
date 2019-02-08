# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class InvoiceGetReferenceTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super(InvoiceGetReferenceTest, cls).setUpClass()

        cls.invoice = cls.init_invoice('out_invoice')

    def test_get_reference_finnish_invoice(self):
        self.assertFalse(self.invoice.invoice_payment_ref)
        self.invoice.journal_id.invoice_reference_model = 'fi'
        self.invoice.post()
        self.assertTrue(self.invoice.invoice_payment_ref)

    def test_get_reference_finnish_partner(self):
        self.assertFalse(self.invoice.invoice_payment_ref)
        self.invoice.journal_id.invoice_reference_type = 'partner'
        self.invoice.journal_id.invoice_reference_model = 'fi'
        self.invoice.post()
        self.assertTrue(self.invoice.invoice_payment_ref)

    def test_get_reference_finnish_rf_invoice(self):
        self.assertFalse(self.invoice.invoice_payment_ref)
        self.invoice.journal_id.invoice_reference_model = 'fi_rf'
        self.invoice.post()
        self.assertTrue(self.invoice.invoice_payment_ref)

    def test_get_reference_finnish_rf_partner(self):
        self.assertFalse(self.invoice.invoice_payment_ref)
        self.invoice.journal_id.invoice_reference_type = 'partner'
        self.invoice.journal_id.invoice_reference_model = 'fi_rf'
        self.invoice.post()
        self.assertTrue(self.invoice.invoice_payment_ref)
