# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class InvoiceGetReferenceTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_fi.fi_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

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
