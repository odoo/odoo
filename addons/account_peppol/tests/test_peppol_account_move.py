from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPeppolAccountMove(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].is_account_peppol_participant = True
        cls.invoice = cls.init_invoice('out_invoice', products=cls.product_a)

    def test_peppol_invoice_set_customer_ref(self):
        self.assertFalse(self.invoice.ref)
        self.invoice.action_post()
        self.assertEqual(self.invoice.ref, self.invoice.payment_reference)

    def test_peppol_invoice_keep_customer_ref(self):
        self.invoice.ref = 'MYREF'
        self.invoice.action_post()
        self.assertEqual(self.invoice.ref, 'MYREF')
