from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestBhAccountMove(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('bh')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].vat = '200000000000003'
        cls.partner_a.write({'is_company': True, 'vat': '200000000000004'})
        cls.partner_b.vat = False

    def test_invoice_title_registered_customer(self):
        invoice = self._create_invoice_one_line(price_unit=100.0, partner_id=self.partner_a, post=True)
        self.assertEqual(invoice._l10n_gcc_get_invoice_title(), "Tax Invoice")

    def test_invoice_title_contact_of_registered_customer(self):
        contact = self.env['res.partner'].create({'name': 'Contact', 'parent_id': self.partner_a.id})
        contact.vat = False
        invoice = self._create_invoice_one_line(price_unit=100.0, partner_id=contact, post=True)
        self.assertEqual(invoice._l10n_gcc_get_invoice_title(), "Tax Invoice")

    def test_invoice_title_unregistered_customer(self):
        invoice = self._create_invoice_one_line(price_unit=100.0, partner_id=self.partner_b, post=True)
        self.assertEqual(invoice._l10n_gcc_get_invoice_title(), "Simplified Tax Invoice")

    def test_invoice_title_unregistered_company(self):
        self.company_data['company'].vat = False
        invoice = self._create_invoice_one_line(price_unit=100.0, partner_id=self.partner_a, post=True)
        self.assertFalse(invoice._l10n_gcc_get_invoice_title())

    def test_invoice_title_debit_note(self):
        if 'debit_origin_id' not in self.env['account.move']._fields:
            self.skipTest("account_debit_note module not installed")
        invoice = self._create_invoice_one_line(price_unit=100.0, partner_id=self.partner_a, post=True)
        debit_note = invoice.copy({'debit_origin_id': invoice.id})
        self.assertFalse(debit_note._l10n_gcc_get_invoice_title())
