# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tools import is_valid_structured_reference_si
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10n_siInvoiceGetReferenceTest(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('si')
    def setUpClass(cls):
        super().setUpClass()

        cls.invoice = cls.init_invoice('out_invoice', products=cls.product_a + cls.product_b)

    def test_get_reference_slovenian_invoice(self):
        self.assertFalse(self.invoice.payment_reference)
        self.invoice.journal_id.invoice_reference_model = 'si'
        self.invoice.action_post()
        self.assertTrue(is_valid_structured_reference_si(self.invoice.payment_reference))

    def test_get_reference_slovenian_partner(self):
        self.assertFalse(self.invoice.payment_reference)
        self.invoice.journal_id.invoice_reference_type = 'partner'
        self.invoice.journal_id.invoice_reference_model = 'si'
        self.invoice.action_post()
        self.assertTrue(is_valid_structured_reference_si(self.invoice.payment_reference))
