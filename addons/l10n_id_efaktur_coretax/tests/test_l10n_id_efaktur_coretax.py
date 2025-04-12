# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import Command, tools
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

@tagged('post_install', '-at_install', 'post_install_l10n')
class TestEfakturCoretax(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        """
        1) contact with l10n_id_pkp with l10n_id_kode_transaksi=04
        2) use 11% tax
        """
        super().setUpClass(chart_template_ref="id")

        cls.company_data['company'].street = "test"
        cls.company_data['company'].phone = "12345"
        cls.company_data['company'].vat = "1234567890123456"

        cls.partner_a.write({"l10n_id_pkp": True, "l10n_id_kode_transaksi": "04", "vat": "1234567890123457", "country_id": cls.env.ref('base.id').id})
        cls.tax_sale_a.amount = 11.0
        cls.tax_incl = cls.env['account.tax'].create({"name": "tax include 11", "type_tax_use": "sale", "amount": 11.0, "price_include": True})

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
        """ Test result of regular valid invoice with 04 transaction code.

        Expected is OtherTaxBase=TaxBase and VATRate follows the actual amount of the tax
        """

        out_invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1})
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
                <OtherTaxBase>100000.0</OtherTaxBase>
            </xpath>
            <xpath expr="//VATRate" position="replace">
                <VATRate>11.0</VATRate>
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
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1})
            ],
            'l10n_id_kode_transaksi': '07',
            'l10n_id_coretax_add_info_07': 'TD.00505',
            'l10n_id_coretax_custom_doc': 'custom doc',
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
                <OtherTaxBase>100000.0</OtherTaxBase>
            </xpath>
            <xpath expr="//VATRate" position="replace">
                <VATRate>11.0</VATRate>
            </xpath>
            <xpath expr="//VAT" position="replace">
                <VAT>11000.0</VAT>
            </xpath>
            <xpath expr="//CustomDoc" position="replace">
                <CustomDoc>custom doc</CustomDoc>
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
            'l10n_id_kode_transaksi': '01',
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
                    <TrxCode>01</TrxCode>
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
                        <Price>100000.0</Price>
                        <Qty>1.0</Qty>
                        <TotalDiscount>0.0</TotalDiscount>
                        <TaxBase>100000.0</TaxBase>
                        <OtherTaxBase>100000.0</OtherTaxBase>
                        <VATRate>11.0</VATRate>
                        <VAT>11000.0</VAT>
                        <STLGRate>0.0</STLGRate>
                        <STLG>0.0</STLG>
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
                    <Price>100000.0</Price>
                    <Qty>1.0</Qty>
                    <TotalDiscount>0.0</TotalDiscount>
                    <TaxBase>100000.0</TaxBase>
                    <OtherTaxBase>91666.67</OtherTaxBase>
                    <VATRate>12</VATRate>
                    <VAT>11000.0</VAT>
                    <STLGRate>0.0</STLGRate>
                    <STLG>0.0</STLG>
                </GoodService>
            </xpath>
            '''
        )

        self.assertXmlTreeEqual(result_tree, expected_tree)

    def test_efaktur_xml_luxury_goods(self):
        """ Test that when selling product that involves the luxury good tax, STLGRate and STLG
        should be filled in """

        company_id = self.company_data['company'].id
        luxury_tax = self.env['account.tax'].create(
            {
                "name": "luxury tax",
                "type_tax_use": "sale",
                "amount": 20.0,
                "tax_group_id": self.env.ref(f'account.{company_id}_l10n_id_tax_group_luxury_goods').id
            }
        )

        out_invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'name': 'line1', 'price_unit': 100000, 'quantity': 1, 'tax_ids': [luxury_tax.id, self.tax_sale_a.id]}),
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
                <OtherTaxBase>100000.0</OtherTaxBase>
            </xpath>
            <xpath expr="//VATRate" position="replace">
                <VATRate>11.0</VATRate>
            </xpath>
            <xpath expr="//STLGRate" position="replace">
                <STLGRate>20.0</STLGRate>
            </xpath>
            <xpath expr="//STLG" position="replace">
                <STLG>20000.0</STLG>
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
                <Price>100000.0</Price>
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
                <Price>100000.0</Price>
            </xpath>
            <xpath expr="//TotalDiscount" position="replace">
                <TotalDiscount>10000.0</TotalDiscount>
            </xpath>
            <xpath expr="//TaxBase" position="replace">
                <TaxBase>90000.0</TaxBase>
            </xpath>
            <xpath expr="//OtherTaxBase" position="replace">
                <OtherTaxBase>82500.0</OtherTaxBase>
            </xpath>
            <xpath expr="//VAT" position="replace">
                <VAT>9900.0</VAT>
            </xpath>
            '''
        )

        self.assertXmlTreeEqual(result_tree, expected_tree)
