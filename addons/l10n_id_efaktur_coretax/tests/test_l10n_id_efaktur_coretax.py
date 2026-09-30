# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import Command, tools
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestEfakturCoretax(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('id')
    def setUpClass(cls):
        """
        1) contact with l10n_id_pkp with l10n_id_kode_transaksi=04
        2) use 11% tax
        """
        super().setUpClass()

        cls.company_data['company'].street = "test"
        cls.company_data['company'].phone = "12345"
        cls.company_data['company'].vat = "1234567890123456"

        cls.company_data_2 = cls.setup_other_company()

        cls.partner_a.write({"l10n_id_pkp": True, "l10n_id_kode_transaksi": "04", "vat": "1234567890123457", "country_id": cls.env.ref('base.id').id})
        cls.tax_sale_a.amount = 11.0
        cls.tax_incl = cls.env['account.tax'].create({"name": "tax include 11", "type_tax_use": "sale", "amount": 11.0, "price_include_override": "tax_included"})

        company_id = cls.company_data['company'].id
        ChartTemplate = cls.env['account.chart.template'].with_company(company_id)
        cls.luxury_tax = ChartTemplate.ref(f'account.{company_id}_tax_ST3')
        cls.non_luxury_tax = ChartTemplate.ref(f'account.{company_id}_tax_ST4')
        cls.stlg_tax = ChartTemplate.ref(f'account.{company_id}_tax_luxury_sales')
        cls.zero_tax = ChartTemplate.ref(f'account.{company_id}_tax_ST0')

        path = "l10n_id_efaktur_coretax/tests/results/sample.xml"
        with tools.file_open(path, mode='rb') as test_file:
            cls.sample_xml = test_file.read()

    def test_product_code_default(self):
        """ Test interaction when changing the product type between 'consu' and 'service' which
        will trigger change in `l10n_id_product_code` """

        product = self.env['product.template'].create({
            "name": "test product",
            "type": "consu"
        })
        self.assertEqual(product.l10n_id_product_code, self.env.ref('l10n_id_efaktur_coretax.product_code_000000_goods'))

        product.type = "service"
        self.assertEqual(product.l10n_id_product_code, self.env.ref('l10n_id_efaktur_coretax.product_code_000000_service'))

    def test_efaktur_change_facility_add_info(self):
        """ Test that changing FacilityInfo would trigger change in AddInfo and vice versa
        when code transaction is 07 or 08"""

        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100000, 'quantity': 1})
            ],
            'l10n_id_kode_transaksi': '07',
        })

        # AddInfo and FacilityInfo changes in code 07
        out_invoice.l10n_id_coretax_add_info_07 = "TD.00504"
        self.assertEqual(out_invoice.l10n_id_coretax_facility_info_07, "TD.01104")
        out_invoice.l10n_id_coretax_facility_info_07 = "TD.01110"
        self.assertEqual(out_invoice.l10n_id_coretax_add_info_07, "TD.00510")

        # AddInfo and FacilityInfo in code 08
        out_invoice.l10n_id_kode_transaksi = '08'

        out_invoice.l10n_id_coretax_add_info_08 = "TD.00508"
        self.assertEqual(out_invoice.l10n_id_coretax_facility_info_08, "TD.01108")
        out_invoice.l10n_id_coretax_facility_info_08 = "TD.01102"
        self.assertEqual(out_invoice.l10n_id_coretax_add_info_08, "TD.00502")

    # ==================================================
    # Test conditions that dont allow efaktur generation
    # =================================================

    def _verify_error_message(self, ex, err_count, messages=[]):
        """ Verify that there are `err_count` number of errors and that all snippets of messages
        exist in the error message
        """
        exception_msg = str(ex.exception)
        actual_count = len(exception_msg.split('\n')) - 1  # -1 because the first line of error message ("Unable to Download ...") is always there

        self.assertEqual(actual_count, err_count)
        self.assertTrue(all(msg in exception_msg for msg in messages))

    def test_download_efaktur_invalid_invoice(self):
        """ Test to ensure conditions related to invoice are enforced when downloading E-Faktur
        we will test it out
        """

        # Report it not having an invoice
        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100000, 'quantity': 1})
            ],
        })
        vendor_bill.action_post()

        with self.assertRaisesRegex(ValidationError, "not an invoice"):
            vendor_bill.download_efaktur()

        # Report invoice still in draft state
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100000, 'quantity': 1})
            ],
        })

        with self.assertRaisesRegex(ValidationError, "in draft state"):
            out_invoice.download_efaktur()

        # Report invoice contains no taxes
        out_invoice_no_tax = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100000, 'quantity': 1, 'tax_ids': []})
            ],
        })
        out_invoice_no_tax.action_post()

        with self.assertRaisesRegex(ValidationError, "does not contain any taxes"):
            out_invoice_no_tax.download_efaktur()

        # Report invoice contains no ppn taxes but have new tax with new created tax group
        new_tax = self.env["account.tax"].create({
            'type_tax_use': 'sale',
            'name': 'PPH',
            'amount': -5.0,
            'tax_group_id': self.env["account.tax.group"].create({'name': 'PPH Tax Group'}).id,
        })
        out_invoice_with_new_tax_group_and_no_ppn_taxes = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100000, 'quantity': 1, 'tax_ids': [new_tax.id]})
            ],
        })
        out_invoice_with_new_tax_group_and_no_ppn_taxes.action_post()

        with self.assertRaisesRegex(
            ValidationError,
            r"need to have at least one PPN or STLG tax group."
        ):
            out_invoice_with_new_tax_group_and_no_ppn_taxes.download_efaktur()

        # Report invoice contains luxury and non-luxury
        out_invoice_luxury_non_luxury = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100000, 'quantity': 1, 'tax_ids': [self.luxury_tax.id, self.non_luxury_tax.id]})
            ],
        })
        out_invoice_luxury_non_luxury.action_post()

        with self.assertRaisesRegex(
            ValidationError,
            r"can only have one PPN tax group \(excluding STLG\)[\s\S]*Luxury-Goods and Non-Luxury-Goods taxes"
        ):
            out_invoice_luxury_non_luxury.download_efaktur()

        # Report invoice contains stlg and non-luxury
        out_invoice_stlg_non_luxury = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100000, 'quantity': 1, 'tax_ids': [self.non_luxury_tax.id, self.stlg_tax.id]})
            ],
        })
        out_invoice_stlg_non_luxury.action_post()

        with self.assertRaisesRegex(
            ValidationError,
            r"contains both Non-Luxury-Goods and STLG taxes.[\s\S]*has STLG tax but missing the required Luxury-Goods tax."
        ):
            out_invoice_stlg_non_luxury.download_efaktur()

        # Report invoice with code other than 07/08 with zero rate tax
        out_invoice_zero_tax = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100000, 'quantity': 1, 'tax_ids': [self.zero_tax.id]})
            ],
            'l10n_id_kode_transaksi': '04',
        })
        out_invoice_zero_tax.action_post()

        with self.assertRaisesRegex(ValidationError, r".*does not allow 0% \(Zero-rated or Exempt\) taxes\."):
            out_invoice_zero_tax.download_efaktur()

        # Report invoice with code 07/08 with not zero rate tax
        out_invoice_zero_tax_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100000, 'quantity': 1, 'tax_ids': [self.non_luxury_tax.id]})
            ],
            'l10n_id_kode_transaksi': '07',
        })
        out_invoice_zero_tax_2.action_post()

        with self.assertRaisesRegex(ValidationError, r".*must always have tax amount 0"):
            out_invoice_zero_tax_2.download_efaktur()

    def test_download_efaktur_invalid_customer(self):
        """ Test to ensure conditions related to customers are enforced when downloading E-Faktur """
        # Create general partner and change information one by one
        partner = self.env['res.partner'].create({
            'name': "test partner"
        })

        # Nothing is configured yet
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100000, 'quantity': 1})
            ],
        })
        out_invoice.action_post()

        for msg in ["NPWP for customer", "is not taxable", "No country is set"]:
            with self.assertRaisesRegex(ValidationError, msg):
                out_invoice.download_efaktur()

        # activate PKP, fill in VAT, change document type to passport
        partner.vat = "1234567890123478"
        partner.l10n_id_pkp = True
        partner.l10n_id_buyer_document_type = 'Passport'
        partner.country_id = self.env.ref('base.id')

        with self.assertRaisesRegex(ValidationError, "Document number for customer"):
            out_invoice.download_efaktur()

    def test_efaktur_invalid_kode_07_08(self):
        """ Test to extra fields are filled in when code 07 or 08 is used """
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100000, 'quantity': 1})
            ],
            'l10n_id_kode_transaksi': '07',
        })

        out_invoice.action_post()

        with self.assertRaisesRegex(ValidationError, "Kode 07"):
            out_invoice.download_efaktur()

        out_invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100000, 'quantity': 1})
            ],
            'l10n_id_kode_transaksi': '08',
        })
        out_invoice_2.action_post()

        with self.assertRaisesRegex(ValidationError, "Kode 08"):
            out_invoice_2.download_efaktur()

    # ============================
    # Test eFaktur XML content
    # ============================

    def test_efaktur_xml_partner_edit(self):
        """ Test the effect of changing customer information/fields towards the generated XML content"""
        self.partner_a.write({
            "vat": "1234567890999999",
            "l10n_id_tku": "222222",
            "l10n_id_buyer_document_type": "Passport",
            "l10n_id_buyer_document_number": "A123456",
            "l10n_id_pkp": True,
        })

        out_invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1})
            ],
            'l10n_id_kode_transaksi': '04',
        })
        out_invoice.action_post()
        out_invoice.download_efaktur()

        result_tree = etree.fromstring(out_invoice.l10n_id_coretax_document._generate_efaktur_invoice())
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.sample_xml),
            '''
            <xpath expr="//BuyerTin" position="replace">
                <BuyerTin>0000000000000000</BuyerTin>
            </xpath>
            <xpath expr="//BuyerDocument" position="replace">
                <BuyerDocument>Passport</BuyerDocument>
            </xpath>
            <xpath expr="//BuyerDocumentNumber" position="replace">
                <BuyerDocumentNumber>A123456</BuyerDocumentNumber>
            </xpath>
            <xpath expr="//BuyerIDTKU" position="replace">
                <BuyerIDTKU>1234567890999999222222</BuyerIDTKU>
            </xpath>
            '''
        )

        self.assertXmlTreeEqual(result_tree, expected_tree)

    def test_efaktur_xml_trx_04(self):
        """ Test result of regular valid invoice with 04 transaction code.
        Expected to see OtherTaxBase having 11/12 of the actual TaxBase calculated
        """

        out_invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1})
            ],
            'l10n_id_kode_transaksi': '04',
        })
        out_invoice.action_post()
        out_invoice.download_efaktur()

        result_tree = etree.fromstring(out_invoice.l10n_id_coretax_document._generate_efaktur_invoice())
        expected_tree = etree.fromstring(self.sample_xml)

        self.assertXmlTreeEqual(result_tree, expected_tree)

    def test_efaktur_xml_trx_01(self):
        """ Test that with transaction code 01, OtherTaxBase should equal to TaxBase."""

        out_invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1, 'tax_ids': [self.non_luxury_tax.id]})
            ],
            'l10n_id_kode_transaksi': '01',
        })

        out_invoice.action_post()
        out_invoice.download_efaktur()

        result_tree = etree.fromstring(out_invoice.l10n_id_coretax_document._generate_efaktur_invoice())
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.sample_xml),
            '''
            <xpath expr="//TrxCode" position="replace">
                <TrxCode>01</TrxCode>
            </xpath>
            <xpath expr="//OtherTaxBase" position="replace">
                <OtherTaxBase>100000.00</OtherTaxBase>
            </xpath>
            <xpath expr="//TaxBase" position="replace">
                <TaxBase>100000.00</TaxBase>
            </xpath>
            <xpath expr="//VATRate" position="replace">
                <VATRate>12</VATRate>
            </xpath>
            <xpath expr="//VAT" position="replace">
                <VAT>12000.00</VAT>
            </xpath>
            '''
        )

        self.assertXmlTreeEqual(result_tree, expected_tree)

    def test_efaktur_xml_trx_07(self):
        """ Test that with transaction code 07, if we fill in the AddInfo, FacilityStamp, and
        CustomDoc. These components in XML should be filled as a result.

        Result of test should also work for code 08
        """

        out_invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1, 'tax_ids': [self.zero_tax.id]})
            ],
            'l10n_id_kode_transaksi': '07',
            'l10n_id_coretax_add_info_07': 'TD.00505',
            'l10n_id_coretax_custom_doc': 'custom doc',
            'l10n_id_coretax_custom_doc_month_year': '2019-05-01',
        })

        out_invoice.action_post()
        out_invoice.download_efaktur()

        result_tree = etree.fromstring(out_invoice.l10n_id_coretax_document._generate_efaktur_invoice())
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.sample_xml),
            '''
            <xpath expr="//AddInfo" position="replace">
                <AddInfo>TD.00505</AddInfo>
            </xpath>
            <xpath expr="//TrxCode" position="replace">
                <TrxCode>07</TrxCode>
            </xpath>
            <xpath expr="//FacilityStamp" position="replace">
                <FacilityStamp>TD.01105</FacilityStamp>
            </xpath>
            <xpath expr="//OtherTaxBase" position="replace">
                <OtherTaxBase>91666.67</OtherTaxBase>
            </xpath>
            <xpath expr="//VATRate" position="replace">
                <VATRate>12</VATRate>
            </xpath>
            <xpath expr="//VAT" position="replace">
                <VAT>11000.00</VAT>
            </xpath>
            <xpath expr="//CustomDoc" position="replace">
                <CustomDoc>custom doc</CustomDoc>
            </xpath>
            <xpath expr="//CustomDocMonthYear" position="replace">
                <CustomDocMonthYear>052019</CustomDocMonthYear>
            </xpath>
            '''
        )

        self.assertXmlTreeEqual(result_tree, expected_tree)

    def test_efaktur_xml_multiple_invoices(self):
        """ Test the content of XML when generating 1 efaktur from multiple invoices
        Expected to see multiple <TaxInvoice> within the <ListOfTaxInvoice> in the XML
        """

        # create 2 invoices containint different price
        out_invoice_1 = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1})
            ],
            'l10n_id_kode_transaksi': '04',
        })

        out_invoice_2 = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1})
            ],
            'l10n_id_kode_transaksi': '04',
        })

        out_invoice_1.action_post()
        out_invoice_2.action_post()
        invoices = out_invoice_1 + out_invoice_2
        invoices.download_efaktur()

        result_tree = etree.fromstring(invoices.l10n_id_coretax_document._generate_efaktur_invoice())
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.sample_xml),
            '''
            <xpath expr="//ListOfTaxInvoice" position="inside">
                <TaxInvoice>
                    <TaxInvoiceDate>2019-05-01</TaxInvoiceDate>
                    <TaxInvoiceOpt>Normal</TaxInvoiceOpt>
                    <TrxCode>04</TrxCode>
                    <AddInfo/>
                    <CustomDoc/>
                    <CustomDocMonthYear/>
                    <RefDesc>INV/2019/00002</RefDesc>
                    <FacilityStamp/>
                    <SellerIDTKU>1234567890123456000000</SellerIDTKU>
                    <BuyerTin>1234567890123457</BuyerTin>
                    <BuyerDocument>TIN</BuyerDocument>
                    <BuyerCountry>IDN</BuyerCountry>
                    <BuyerDocumentNumber/>
                    <BuyerName>partner_a</BuyerName>
                    <BuyerAdress>Indonesia</BuyerAdress>
                    <BuyerEmail/>
                    <BuyerIDTKU>1234567890123457000000</BuyerIDTKU>
                    <ListOfGoodService>
                        <GoodService>
                        <Opt>A</Opt>
                        <Code>000000</Code>
                        <Name>product_a</Name>
                        <Unit>UM.0018</Unit>
                        <Price>100000.00</Price>
                        <Qty>1.0</Qty>
                        <TotalDiscount>0.00</TotalDiscount>
                        <TaxBase>100000.00</TaxBase>
                        <OtherTaxBase>91666.67</OtherTaxBase>
                        <VATRate>12</VATRate>
                        <VAT>11000.00</VAT>
                        <STLGRate>0.0</STLGRate>
                        <STLG>0.00</STLG>
                        </GoodService>
                    </ListOfGoodService>
                </TaxInvoice>
            </xpath>
            '''
        )

        self.assertXmlTreeEqual(result_tree, expected_tree)

    def test_efaktur_xml_multiple_lines(self):
        """ Test XML content of an invoice containing multiple invoice lines (which also includes
        a "description" line.

        Expected to see multiple <GoodService> within <ListOfGoodService> tag and the
        line should be excluded from the XML description
        """
        product_2 = self.env['product.product'].create({'name': "Product B"})

        out_invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1}),
                (0, 0, {'name': 'description', 'display_type': 'line_note'}),
                (0, 0, {'product_id': product_2.id, 'name': 'line2', 'price_unit': 100000, 'quantity': 1})
            ],
            'l10n_id_kode_transaksi': '04',
        })
        out_invoice.action_post()
        out_invoice.download_efaktur()

        result_tree = etree.fromstring(out_invoice.l10n_id_coretax_document._generate_efaktur_invoice())
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.sample_xml),
            '''
            <xpath expr="//ListOfGoodService" position="inside">
                <GoodService>
                    <Opt>A</Opt>
                    <Code>000000</Code>
                    <Name>Product B</Name>
                    <Unit>UM.0018</Unit>
                    <Price>100000.00</Price>
                    <Qty>1.0</Qty>
                    <TotalDiscount>0.00</TotalDiscount>
                    <TaxBase>100000.00</TaxBase>
                    <OtherTaxBase>91666.67</OtherTaxBase>
                    <VATRate>12</VATRate>
                    <VAT>11000.00</VAT>
                    <STLGRate>0.0</STLGRate>
                    <STLG>0.00</STLG>
                </GoodService>
            </xpath>
            '''
        )

        self.assertXmlTreeEqual(result_tree, expected_tree)

    def test_efaktur_xml_luxury_goods(self):
        """ Test that when selling product that involves the luxury good tax"""

        out_invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1, 'tax_ids': [self.luxury_tax.id]}),
            ],
            'l10n_id_kode_transaksi': '04',
        })
        out_invoice.action_post()
        out_invoice.download_efaktur()

        result_tree = etree.fromstring(out_invoice.l10n_id_coretax_document._generate_efaktur_invoice())
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.sample_xml),
            '''
            <xpath expr="//TrxCode" position="replace">
                <TrxCode>04</TrxCode>
            </xpath>
            <xpath expr="//OtherTaxBase" position="replace">
                <OtherTaxBase>100000.00</OtherTaxBase>
            </xpath>
            <xpath expr="//VAT" position="replace">
                <VAT>12000.00</VAT>
            </xpath>
            <xpath expr="//VATRate" position="replace">
                <VATRate>12</VATRate>
            </xpath>
            '''
        )
        self.assertXmlTreeEqual(result_tree, expected_tree)

    def test_efaktur_xml_luxury_goods_stlg(self):
        """ Test that when selling product that involves the luxury good tax, STLGRate and STLG
        should be filled in """

        out_invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1, 'tax_ids': [self.luxury_tax.id, self.stlg_tax.id]}),
            ],
            'l10n_id_kode_transaksi': '04',
        })
        out_invoice.action_post()
        out_invoice.download_efaktur()

        result_tree = etree.fromstring(out_invoice.l10n_id_coretax_document._generate_efaktur_invoice())
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.sample_xml),
            '''
            <xpath expr="//TrxCode" position="replace">
                <TrxCode>04</TrxCode>
            </xpath>
            <xpath expr="//OtherTaxBase" position="replace">
                <OtherTaxBase>100000.00</OtherTaxBase>
            </xpath>
            <xpath expr="//VAT" position="replace">
                <VAT>12000.00</VAT>
            </xpath>
            <xpath expr="//VATRate" position="replace">
                <VATRate>12</VATRate>
            </xpath>
            <xpath expr="//STLGRate" position="replace">
                <STLGRate>20.0</STLGRate>
            </xpath>
            <xpath expr="//STLG" position="replace">
                <STLG>20000.00</STLG>
            </xpath>
            '''
        )
        self.assertXmlTreeEqual(result_tree, expected_tree)

    def test_invoice_user_main_contact(self):
        """ Test to ensure that we are always using the address of the
        customer(partner_id) on the invoice while some legal fields
        (Is PKP, VAT, Document type, document number, ..) should use from main contact """

        partner_a_invoice = self.env['res.partner'].create({
            "name": "partner_a invoice",
            "type": "invoice",
            "parent_id": self.partner_a.id,
            "street": "invoice address",
            "country_id": self.env.ref('base.id').id,
        })
        out_invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': partner_a_invoice.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1})
            ],
            'l10n_id_kode_transaksi': '04',
        })
        out_invoice.action_post()
        out_invoice.download_efaktur()

        result_tree = etree.fromstring(out_invoice.l10n_id_coretax_document._generate_efaktur_invoice())
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.sample_xml),
            '''
            <xpath expr="//BuyerName" position="replace">
                <BuyerName>partner_a invoice</BuyerName>
            </xpath>
            <xpath expr="//BuyerAdress" position="replace">
                <BuyerAdress>invoice address     Indonesia</BuyerAdress>
            </xpath>
            '''
        )

        self.assertXmlTreeEqual(result_tree, expected_tree)

    def test_efaktur_tax_include(self):
        """ Test when tax configuration is tax included in price should affect price calculation """

        # create invoice containing this
        move = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 111000, 'quantity': 1, 'tax_ids': [self.tax_incl.id]}),
            ],
            'l10n_id_kode_transaksi': '04',
        })
        move.action_post()
        move.download_efaktur()

        result_tree = etree.fromstring(move.l10n_id_coretax_document._generate_efaktur_invoice())
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.sample_xml),
            '''
            <xpath expr="//Price" position="replace">
                <Price>100000.00</Price>
            </xpath>
            '''
        )

        self.assertXmlTreeEqual(result_tree, expected_tree)

    def test_efaktur_tax_include_with_discount(self):
        """ Test when tax configuration is tax included in price and we also invovle discount in price calculation """

        # create invoice containing this
        move = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 111000, 'quantity': 1, 'tax_ids': [self.tax_incl.id], 'discount': 10}),
            ],
            'l10n_id_kode_transaksi': '04',
        })
        move.action_post()
        move.download_efaktur()

        result_tree = etree.fromstring(move.l10n_id_coretax_document._generate_efaktur_invoice())
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.sample_xml),
            '''
            <xpath expr="//Price" position="replace">
                <Price>100000.00</Price>
            </xpath>
            <xpath expr="//TotalDiscount" position="replace">
                <TotalDiscount>10000.00</TotalDiscount>
            </xpath>
            <xpath expr="//TaxBase" position="replace">
                <TaxBase>90000.00</TaxBase>
            </xpath>
            <xpath expr="//OtherTaxBase" position="replace">
                <OtherTaxBase>82500.00</OtherTaxBase>
            </xpath>
            <xpath expr="//VAT" position="replace">
                <VAT>9900.00</VAT>
            </xpath>
            '''
        )

        self.assertXmlTreeEqual(result_tree, expected_tree)

    def test_efaktur_download_multi_company(self):
        """ Ensure that generating efaktur document for invoices across multi company is not allowed """
        # Setup company
        company_2 = self.company_data_2['company']
        tax_id = self.env['account.tax'].create({"name": "test tax", "type_tax_use": "sale", "amount": 10.0, "price_include": True, "company_id": company_2.id})

        # Setup company across 2 companies
        invoices = self.env["account.move"].create([{
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_sale_a.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
            "company_id": self.company.id,
        }, {
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
            "company_id": company_2.id
        }])

        invoices.action_post()

        # Should raise error because the 2 invoices are from 2 different companies
        with self.assertRaises(UserError):
            (invoices).download_efaktur()

    def test_efaktur_download_separate(self):
        """ Test that when we download separately on 2 invoices, each will link to different document.
        If we try to download the 2 together, a RedirectWarning should be raised """

        # Create 2 invoices
        invoices = self.env["account.move"].create([{
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_sale_a.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        } for i in range(2)])

        invoices.action_post()

        # Download efaktur separately
        invoices[0].download_efaktur()
        invoices[1].download_efaktur()

        # l10n_id_efaktur_document should be filled in both documents AND different from each other
        self.assertTrue(invoices[0].l10n_id_coretax_document)
        self.assertTrue(invoices[1].l10n_id_coretax_document)
        self.assertNotEqual(invoices[0].l10n_id_coretax_document, invoices[1].l10n_id_coretax_document)

        # If we try to download together, a RedirectWarning should be raised
        with self.assertRaises(RedirectWarning):
            invoices.download_efaktur()

    def test_efaktur_download_together(self):
        """ Test that when we download efaktur for 2 invoices together, they will refer to the same document
        If we try to download separately on both invoices, RedirectWarning should be raised. """

        # Create 2 invoices
        invoices = self.env["account.move"].create([{
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_sale_a.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        } for i in range(2)])

        invoices.action_post()

        # Download efaktur together
        invoices.download_efaktur()

        # document should be filled in and both invoice should refer to the same document
        self.assertTrue(invoices[0].l10n_id_coretax_document)
        self.assertTrue(invoices[1].l10n_id_coretax_document)
        self.assertEqual(invoices[0].l10n_id_coretax_document, invoices[1].l10n_id_coretax_document)

        # If we try to download separately, RedirectWarning should be raised
        with self.assertRaises(RedirectWarning):
            invoices[0].download_efaktur()
        with self.assertRaises(RedirectWarning):
            invoices[1].download_efaktur()

    def test_efaktur_download_mismatch_flow(self):
        """ Test the flow when you generate 3 invoices (inv1, inv2, ine) generate document(1) and
        document(2,3). When we try to download inv(1,2) redirect warning would be raised, and it should
        provide the view of 2 documents concerned. Then, we edit such that document(1) adds invoice 2.
        Afterwards, regenerate both documents. We are expected to be able to download invoice(1,2) without error now,
        while also still using the same efaktur document record as before """

        # Generate 3 invoices
        invoices = self.env["account.move"].create([{
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_sale_a.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        } for i in range(3)])
        invoices.action_post()

        # Generate document in group (1), and (2, 3)
        invoices[0].download_efaktur()
        invoices[1:].download_efaktur()

        # Suppose now we want to generate for (1, 2, 3) instead, it should trigger a redirect warning
        # that includes information on the efaktur document involved

        with self.assertRaises(RedirectWarning) as error:
            invoices[:2].download_efaktur()

        action = error.exception.args[1]
        document_ids = action['domain'][0][2]

        # Make sure the documents involved are only the between the document of 1, 2, and 3
        self.assertEqual(document_ids, invoices.l10n_id_coretax_document.ids)

        # Store old document id and attachment for before-after comparison in the end
        old_document = invoices[0].l10n_id_coretax_document

        # Unlink invoice 3 from 2nd document, link to first document and regenerate both the document attachments
        document_to_edit = self.env['l10n_id_efaktur_coretax.document'].browse(document_ids)
        document_to_edit[1].invoice_ids = [Command.unlink(invoices[1].id)]
        document_to_edit[1].action_regenerate()

        document_to_edit[0].invoice_ids = [Command.link(invoices[1].id)]
        document_to_edit[0].action_regenerate()

        # Should allow download of invoice(1,2,3) together where the efaktur document is the same as
        # the old invoice 1's document
        invoices[:2].download_efaktur()
        self.assertEqual(invoices[1].l10n_id_coretax_document, old_document)

    def test_efaktur_with_new_tax_group(self):
        """ Test efaktur with move line using new created tax & tax groups along with the luxury tax,
        expected to work as normal and the new tax group not considered as regular tax which will make the
        OtherTaxBase has 11/12 of the original value"""
        # create new tax and new group
        new_tax = self.env["account.tax"].create({
            'type_tax_use': 'sale',
            'name': 'PPH',
            'amount': -5.0,
            'tax_group_id': self.env["account.tax.group"].create({'name': 'PPH Tax Group'}).id,
            'price_include_override': 'tax_included'
        })

        # create invoice containing the new tax along with one of the ppn tax group
        move = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1, 'tax_ids': [new_tax.id, self.luxury_tax.id]}),
            ],
            'l10n_id_kode_transaksi': '04',
        })
        move.action_post()
        move.download_efaktur()

        result_tree = etree.fromstring(move.l10n_id_coretax_document._generate_efaktur_invoice())
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.sample_xml),
            '''
            <xpath expr="//TrxCode" position="replace">
                <TrxCode>04</TrxCode>
            </xpath>
            <xpath expr="//Price" position="replace">
                <Price>105263.16</Price>
            </xpath>
            <xpath expr="//TaxBase" position="replace">
                <TaxBase>105263.16</TaxBase>
            </xpath>
            <xpath expr="//OtherTaxBase" position="replace">
                <OtherTaxBase>105263.16</OtherTaxBase>
            </xpath>
            <xpath expr="//VAT" position="replace">
                <VAT>12631.58</VAT>
            </xpath>
            <xpath expr="//VATRate" position="replace">
                <VATRate>12</VATRate>
            </xpath>
            '''
        )
        self.assertXmlTreeEqual(result_tree, expected_tree)

    def test_efaktur_with_new_tax_group_in_different_line(self):
        """ Test efaktur with multiple invoice line where one is valid ppn invoice line
        and the other one line have the new created tax group only

        Expected to work since there is a valid invoice line for product_a while
        the <GoodService> for product_b will still show up in the efaktur but their OtherTaxBase, VATRate, VAT are 0"""

        # create new tax and new group
        new_tax = self.env["account.tax"].create({
            'type_tax_use': 'sale',
            'name': 'PPH',
            'amount': -5.0,
            'tax_group_id': self.env["account.tax.group"].create({'name': 'PPH Tax Group'}).id,
        })

        # Create the product and the invoice with 1 valid ppn invoice line and 1 that is not
        product_2 = self.env['product.product'].create({'name': "Product B"})
        out_invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1}),
                (0, 0, {'product_id': product_2.id, 'name': 'line2', 'price_unit': 100000, 'quantity': 1, 'tax_ids': [new_tax.id]})
            ],
            'l10n_id_kode_transaksi': '04',
        })
        out_invoice.action_post()
        out_invoice.download_efaktur()

        result_tree = etree.fromstring(out_invoice.l10n_id_coretax_document._generate_efaktur_invoice())
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.sample_xml),
            '''
            <xpath expr="//ListOfGoodService" position="inside">
                <GoodService>
                    <Opt>A</Opt>
                    <Code>000000</Code>
                    <Name>Product B</Name>
                    <Unit>UM.0018</Unit>
                    <Price>100000.00</Price>
                    <Qty>1.0</Qty>
                    <TotalDiscount>0.00</TotalDiscount>
                    <TaxBase>100000.00</TaxBase>
                    <OtherTaxBase>0.00</OtherTaxBase>
                    <VATRate>0.0</VATRate>
                    <VAT>0.00</VAT>
                    <STLGRate>0.0</STLGRate>
                    <STLG>0.00</STLG>
                </GoodService>
            </xpath>
            '''
        )
        self.assertXmlTreeEqual(result_tree, expected_tree)
