# -*- coding: utf-8 -*-
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.modules.module import get_module_resource


class TestUBL(AccountEdiTestCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_be.l10nbe_chart_template', edi_format_ref='l10n_be_edi.edi_efff_1'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.partner_a.vat = 'BE0477472701'

    def test_invoice_edi_xml_update(self):
        invoice = self._create_empty_vendor_bill()
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('l10n_be_edi', 'test_xml_file', 'efff_test.xml', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 666.50)
        self.assertEqual(invoice.amount_tax, 115.67)
        self.assertEqual(invoice.partner_id, self.partner_a)

    def test_invoice_edi_xml_create(self):
        invoice_count = len(self.env['account.move'].search([]))
        invoice = self.create_invoice_from_file('l10n_be_edi', 'test_xml_file', 'efff_test.xml')
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)
        self.assertEqual(invoice.amount_total, 666.50)
        self.assertEqual(invoice.amount_tax, 115.67)
        self.assertEqual(invoice.partner_id, self.partner_a)

    def test_import_do_not_overwrite_tax(self):
        file_path = get_module_resource('l10n_be_edi', 'test_xml_file', 'efff_test.xml')
        file = open(file_path, 'rb').read()
        original_etree = self.get_xml_tree_from_string(file)

        # Add the information about the tax to the xml : with an absurd amount that couldn't be correct
        applied_xpath = '''
            <xpath expr="//*[local-name()='TaxTotal']/*[local-name()='TaxSubtotal']/*[local-name()='TaxAmount']" position="replace"
                xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
                <cbc:TaxAmount currencyID="EUR">123456.00</cbc:TaxAmount>
            </xpath>
        '''

        etree = self.with_applied_xpath(original_etree, applied_xpath)

        invoice = self.edi_format.with_context(default_move_type='out_invoice')._create_invoice_from_ubl(etree)

        # Ensure that the amount_tax is the one we set in the xml file and not the one computed by odoo
        self.assertEqual(invoice.amount_tax_signed, 123456.00)
