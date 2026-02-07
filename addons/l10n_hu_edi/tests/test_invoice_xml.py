from odoo import tools, fields, Command
from odoo.tests.common import tagged
from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon

from freezegun import freeze_time
import base64
import zipfile
import io


@tagged('post_install_l10n', '-at_install', 'post_install')
class L10nHuEdiTestInvoiceXml(L10nHuEdiTestCommon):
    @classmethod
    def setUpClass(cls):
        with freeze_time('2024-02-01'):
            super().setUpClass()

            cls.company_data['company'].write({
                'bank_ids': [Command.create({
                    'acc_number': 'HU0123456789',
                    'allow_out_payment': True,
                })]
            })
            cls.partner_company.write({
                'bank_ids': [Command.create({
                    'acc_number': 'HU6666666666',
                    'allow_out_payment': True,
                })]
            })
            cls.bank_company = cls.env['res.partner.bank'].create({
                'acc_number': 'HU7357735773',
                'partner_id': cls.company_data['company'].partner_id.id,
                'allow_out_payment': True,
            })
            cls.bank_partner = cls.env['res.partner.bank'].create({
                'acc_number': 'HU9487189480',
                'partner_id': cls.partner_company.id,
                'allow_out_payment': True,
            })

    def test_invoice_and_credit_note(self):
        with freeze_time('2024-02-01'):
            invoice = self.create_invoice_simple()
            invoice.partner_bank_id = self.bank_company
            invoice.action_post()
            invoice._l10n_hu_edi_set_chain_index()
            invoice_xml = invoice._l10n_hu_edi_generate_xml()

            with tools.file_open('l10n_hu_edi/tests/invoice_xmls/invoice_simple.xml', 'rb') as expected_xml_file:
                self.assertXmlTreeEqual(
                    self.get_xml_tree_from_string(invoice_xml),
                    self.get_xml_tree_from_string(expected_xml_file.read()),
                )

            # Set invoice state to 'confirmed', otherwise the credit note can't be sent
            invoice.write({'l10n_hu_edi_state': 'confirmed'})

            credit_note = self.create_reversal(invoice)
            credit_note.partner_bank_id = self.bank_partner
            credit_note.action_post()
            credit_note._l10n_hu_edi_set_chain_index()
            credit_note_xml = credit_note._l10n_hu_edi_generate_xml()

            with tools.file_open('l10n_hu_edi/tests/invoice_xmls/credit_note.xml', 'rb') as expected_xml_file:
                self.assertXmlTreeEqual(
                    self.get_xml_tree_from_string(credit_note_xml),
                    self.get_xml_tree_from_string(expected_xml_file.read()),
                )

    def test_invoice_complex_huf(self):
        with freeze_time('2024-02-01'):
            invoice = self.create_invoice_complex_huf()
            invoice.action_post()
            invoice_xml = invoice._l10n_hu_edi_generate_xml()

            with tools.file_open('l10n_hu_edi/tests/invoice_xmls/invoice_complex_huf.xml', 'rb') as expected_xml_file:
                self.assertXmlTreeEqual(
                    self.get_xml_tree_from_string(invoice_xml),
                    self.get_xml_tree_from_string(expected_xml_file.read()),
                )

    def test_invoice_complex_eur(self):
        with freeze_time('2024-02-01'):
            invoice = self.create_invoice_complex_eur()
            invoice.action_post()
            invoice_xml = invoice._l10n_hu_edi_generate_xml()

            with tools.file_open('l10n_hu_edi/tests/invoice_xmls/invoice_complex_eur.xml', 'rb') as expected_xml_file:
                self.assertXmlTreeEqual(
                    self.get_xml_tree_from_string(invoice_xml),
                    self.get_xml_tree_from_string(expected_xml_file.read()),
                )

    def test_advance_invoice(self):
        # Skip if sale is not installed
        if 'sale_line_ids' not in self.env['account.move.line']:
            self.skipTest('Sale module not installed, skipping advance invoice tests.')
        self.env.user.group_ids += self.env.ref('sales_team.group_sale_salesman')

        # Issue advance invoice on 2024-01-01.
        with freeze_time('2024-01-01'):
            sale_order, advance_invoice = self.create_advance_invoice()
            advance_invoice.action_post()
            advance_invoice_xml = advance_invoice._l10n_hu_edi_generate_xml()

            with tools.file_open('l10n_hu_edi/tests/invoice_xmls/invoice_advance.xml', 'rb') as expected_xml_file:
                self.assertXmlTreeEqual(
                    self.get_xml_tree_from_string(advance_invoice_xml),
                    self.get_xml_tree_from_string(expected_xml_file.read()),
                )

        # Pay advance invoice on 2024-01-15.
        with freeze_time('2024-01-15'):
            self.env['account.payment.register'].with_context(active_ids=advance_invoice.ids, active_model='account.move').create({})._create_payments()

        # Issue final invoice on 2024-02-01. The XML should report 2024-01-15 as the date of advance payment.
        with freeze_time('2024-02-01'):
            final_invoice = self.create_final_invoice(sale_order)
            final_invoice.action_post()
            final_invoice_xml = final_invoice._l10n_hu_edi_generate_xml()

            with tools.file_open('l10n_hu_edi/tests/invoice_xmls/invoice_final.xml', 'rb') as expected_xml_file:
                self.assertXmlTreeEqual(
                    self.get_xml_tree_from_string(final_invoice_xml),
                    self.get_xml_tree_from_string(expected_xml_file.read()),
                )

    def test_tax_audit_export(self):
        with freeze_time('2024-02-01'):
            invoice = self.create_invoice_simple()
            invoice.partner_bank_id = self.bank_company
            invoice.action_post()

            tax_audit_export = self.env['l10n_hu_edi.tax_audit_export'].create({
                'date_from': fields.Date.today(),
                'date_to': fields.Date.today(),
            })
            tax_audit_export.action_export()

            export_file = base64.b64decode(tax_audit_export.export_file)
            with io.BytesIO(export_file) as zip_buffer:
                with zipfile.ZipFile(zip_buffer) as zip_file:
                    filenames = zip_file.namelist()
                    with zip_file.open(filenames[0]) as invoice_file:
                        invoice_xml = invoice_file.read()

            with tools.file_open('l10n_hu_edi/tests/invoice_xmls/invoice_simple.xml', 'rb') as expected_xml_file:
                self.assertXmlTreeEqual(
                    self.get_xml_tree_from_string(invoice_xml),
                    self.get_xml_tree_from_string(expected_xml_file.read()),
                )

    def test_multi_currency_tax_sign(self):
        currency_eur = self.env.ref('base.EUR')

        out_invoice = self.create_invoice_simple(currency=currency_eur)
        in_invoice = self.create_bill_simple(currency=currency_eur)
        out_refund = self.create_credit_note_simple(currency=currency_eur)
        in_refund = self.create_refund_simple(currency=currency_eur)

        expected_value = tools.float_round(10000 * self.tax_vat.amount / (100 * currency_eur.rate), self.currency.decimal_places)

        self.assertEqual(out_invoice._l10n_hu_get_invoice_totals_for_report()['total_vat_amount_in_huf'], expected_value)
        self.assertEqual(in_invoice._l10n_hu_get_invoice_totals_for_report()['total_vat_amount_in_huf'], expected_value)
        self.assertEqual(out_refund._l10n_hu_get_invoice_totals_for_report()['total_vat_amount_in_huf'], -expected_value)
        self.assertEqual(in_refund._l10n_hu_get_invoice_totals_for_report()['total_vat_amount_in_huf'], -expected_value)

    def test_invoice_simple_deduction(self):
        with freeze_time('2024-02-01'):
            invoice = self.create_invoice_simple_discount()
            invoice.action_post()
            invoice_xml = invoice._l10n_hu_edi_generate_xml()

            with tools.file_open('l10n_hu_edi/tests/invoice_xmls/invoice_simple_discount.xml', 'rb') as expected_xml_file:
                self.assertXmlTreeEqual(
                    self.get_xml_tree_from_string(invoice_xml),
                    self.get_xml_tree_from_string(expected_xml_file.read()),
                )

    def test_invoice_tax_price_include(self):
        with freeze_time('2024-02-01'):
            invoice = self.create_invoice_tax_price_include()
            invoice.action_post()
            invoice_xml = invoice._l10n_hu_edi_generate_xml()

            with tools.file_open('l10n_hu_edi/tests/invoice_xmls/invoice_tax_price_include.xml', 'rb') as expected_xml_file:
                self.assertXmlTreeEqual(
                    self.get_xml_tree_from_string(invoice_xml),
                    self.get_xml_tree_from_string(expected_xml_file.read()),
                )
