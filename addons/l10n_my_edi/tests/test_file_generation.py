# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from freezegun import freeze_time
from lxml import etree

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import Form, tagged
from odoo.tools import file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

NS_MAP = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
    'sig': 'urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2',
    'sac': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2',
    'sbc': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2',
    'ds': 'http://www.w3.org/2000/09/xmldsig#',
    'xades': 'http://uri.etsi.org/01903/v1.3.2#',
    'inv': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
}


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nMyEDITestFileGeneration(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('my')
    def setUpClass(cls):
        super().setUpClass()

        cls.other_currency = cls.setup_other_currency('EUR')

        # TIN number is required
        cls.company_data['company'].write({
            'vat': 'C2584563200',
            'l10n_my_edi_mode': 'test',
            'l10n_my_edi_industrial_classification': cls.env['l10n_my_edi.industry_classification'].search([('code', '=', '01111')]).id,
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': '202001234567',
            'state_id': cls.env.ref('base.state_my_jhr').id,
            'street': 'that one street, 5',
            'city': 'Main city',
            'phone': '+60123456789',
        })
        cls.partner_a.write({
            'vat': 'C2584563201',
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': '202001234568',
            'country_id': cls.env.ref('base.my').id,
            'state_id': cls.env.ref('base.state_my_jhr').id,
            'street': 'that other street, 3',
            'city': 'Main city',
            'phone': '+60123456786',
            'l10n_my_edi_industrial_classification': cls.env['l10n_my_edi.industry_classification'].search([('code', '=', '01111')]).id,
            'ref': "MY-REF",
        })
        cls.partner_b.write({
            'vat': 'EI00000000020',
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': 'NA',
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env.ref('base.state_us_1'),
            'street': 'that other street, 3',
            'city': 'Main city',
            'phone': '+60123456785',
            'l10n_my_edi_industrial_classification': cls.env.ref('l10n_my_edi.class_00000', raise_if_not_found=False).id,
        })
        cls.product_a.l10n_my_edi_classification_code = "001"

        cls.purchase_tax = cls.env['account.tax'].create({
            'name': 'tax_10',
            'amount_type': 'percent',
            'amount': 10,
            'type_tax_use': 'purchase',
            'country_id': cls.env.ref('base.my').id,
        })

        cls.fakenow = datetime(2024, 7, 15, 10, 00, 00)
        cls.startClassPatcher(freeze_time(cls.fakenow))

    def test_01_can_generate_file(self):
        """
        Simply test that with a valid configuration, we can generate the file.
        """
        invoice = self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True)
        myinvois_document = invoice._create_myinvois_document()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)

        # The file is working! Now we assert that the specificities needed for this EDI (what you can find in this module) are found in the file.
        root = etree.fromstring(file)

        # 1. Invoice level

        # Validate the invoice type. In this case, an invoice with version 1.1 at the time of writing.
        self._assert_node_values(
            root,
            'cbc:InvoiceTypeCode',
            '01',
            attributes={'listVersionID': '1.1'},
        )

        # Validate that the issue time is present, and correct
        self._assert_node_values(
            root,
            'cbc:IssueTime',
            '10:00:00Z',
        )

        # 2. Supplier party
        supplier_root = root.xpath('cac:AccountingSupplierParty/cac:Party', namespaces=NS_MAP)[0]

        # Industry classification
        self._assert_node_values(
            supplier_root,
            'cbc:IndustryClassificationCode',
            self.company_data['company'].l10n_my_edi_industrial_classification.code,
            attributes={'name': self.company_data['company'].l10n_my_edi_industrial_classification.name},
        )
        # Party Identifications - TIN and BRN (or other type of id) are required. SST & TTX are tested separately.
        self._assert_node_values(
            supplier_root,
            'cac:PartyIdentification/cbc:ID[@schemeID="TIN"]',
            self.company_data['company'].vat,
        )
        self._assert_node_values(
            supplier_root,
            'cac:PartyIdentification/cbc:ID[@schemeID="BRN"]',
            self.company_data['company'].l10n_my_identification_number,
        )

        # Address format
        self._assert_node_values(
            supplier_root,
            'cac:PostalAddress/cac:AddressLine/cbc:Line',
            self.company_data['company'].street,
        )

        # 3. Customer level
        customer_root = root.xpath('cac:AccountingCustomerParty/cac:Party', namespaces=NS_MAP)[0]

        # Party Identifications - TIN and BRN (or other type of id) are required. SST & TTX are tested separately.
        self._assert_node_values(
            customer_root,
            'cac:PartyIdentification/cbc:ID[@schemeID="TIN"]',
            self.partner_a.commercial_partner_id.vat,
        )
        self._assert_node_values(
            customer_root,
            'cac:PartyIdentification/cbc:ID[@schemeID="BRN"]',
            self.partner_a.commercial_partner_id.l10n_my_identification_number,
        )

        # Address format
        self._assert_node_values(
            customer_root,
            'cac:PostalAddress/cac:AddressLine/cbc:Line',
            self.partner_a.street,
        )

        with file_open('l10n_my_edi/tests/expected_xmls/invoice.xml', 'rb') as f:
            expected_xml = etree.fromstring(f.read())
        self.assertXmlTreeEqual(root, expected_xml)

    def test_02_multicurrency(self):
        """
        Simply ensure that in a multi currency environment, the rate is found in the file and is the expected one.
        """
        invoice = self.init_invoice(
            'out_invoice', currency=self.other_currency, taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True
        )
        myinvois_document = invoice._create_myinvois_document()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)

        root = etree.fromstring(file)
        # We should have a tax exchange rate set.
        # The rate is the rate from foreign currency to MYR
        self._assert_node_values(
            root,
            'cac:TaxExchangeRate/cbc:CalculationRate',
            '0.5',
        )
        # Target currency is always MYR
        self._assert_node_values(
            root,
            'cac:TaxExchangeRate/cbc:TargetCurrencyCode',
            'MYR',
        )
        self._assert_node_values(
            root,
            'cac:TaxExchangeRate/cbc:SourceCurrencyCode',
            'EUR',
        )
        # Check that the TaxAmount node has the correct currency too
        self._assert_node_values(
            root,
            'cac:TaxTotal/cbc:TaxAmount',
            text='200.00',
            attributes={'currencyID': 'EUR'},
        )

        with file_open('l10n_my_edi/tests/expected_xmls/invoice_multicurrency.xml', 'rb') as f:
            expected_xml = etree.fromstring(f.read())
        self.assertXmlTreeEqual(root, expected_xml)

    def test_03_optional_fields(self):
        """
        Set a few optional fields, and ensure that they appear as expecting in the file.
        """
        invoice = self.init_invoice(
            'out_invoice', currency=self.other_currency, taxes=self.company_data['default_tax_sale'], products=self.product_a
        )
        invoice.write({
            'invoice_incoterm_id': self.env.ref('account.incoterm_CFR').id,
            'l10n_my_edi_custom_form_reference': 'E12345678912',
        })

        self.company_data['company'].write({
            'sst_registration_number': 'A01-2345-67891012',
            'ttx_registration_number': '123-4567-89012345',
        })
        self.partner_a.commercial_partner_id.sst_registration_number = 'A01-2345-67891013'

        invoice.action_post()
        myinvois_document = invoice._create_myinvois_document()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)

        root = etree.fromstring(file)

        # We test a few values that are optional, yet mandatory in some cases (we leave it up to the user)
        # AdditionalDocumentReference => incoterm and customs
        self._assert_node_values(
            root,
            'cac:AdditionalDocumentReference[not(descendant::*[local-name() = "DocumentType"])]/cbc:ID',
            invoice.invoice_incoterm_id.code,
        )
        self._assert_node_values(
            root,
            'cac:AdditionalDocumentReference[descendant::*[local-name() = "DocumentType"]]/cbc:DocumentType',
            'K2',
        )
        self._assert_node_values(
            root,
            'cac:AdditionalDocumentReference[descendant::*[local-name() = "DocumentType"]]/cbc:ID',
            invoice.l10n_my_edi_custom_form_reference,
        )
        # SST and TTX numbers (tax registrations). SST can be used in both cases, TTX only for supplier.
        # supplier
        self._assert_node_values(
            root,
            'cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID="SST"]',
            self.company_data['company'].sst_registration_number,
        )
        self._assert_node_values(
            root,
            'cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID="TTX"]',
            self.company_data['company'].ttx_registration_number,
        )
        # customer
        self._assert_node_values(
            root,
            'cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID="SST"]',
            self.partner_a.commercial_partner_id.sst_registration_number,
        )

        with file_open('l10n_my_edi/tests/expected_xmls/invoice_optional_fields.xml', 'rb') as f:
            expected_xml = etree.fromstring(f.read())
        self.assertXmlTreeEqual(root, expected_xml)

    def test_04_credit_note(self):
        """
        Ensure that the type is correctly set for another move type, as well as that the original
        uuid is present in an adjustment invoice.
        """
        invoice = self.init_invoice(
            'out_invoice', currency=self.other_currency, taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True,
        )
        invoice_document = invoice._create_myinvois_document()
        # Simulate that the document was sent
        invoice_document.write({
            'myinvois_state': 'valid',
            'myinvois_external_uuid': '12345678912345678912345678',
        })

        action = invoice.action_reverse()
        reversal_wizard = self.env[action['res_model']].with_context(
            active_ids=invoice.ids,
            active_model='account.move',
            default_journal_id=invoice.journal_id.id,
        ).create({})
        action = reversal_wizard.reverse_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_note.action_post()
        myinvois_document = credit_note._create_myinvois_document()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)

        root = etree.fromstring(file)
        # Check the invoice type to endure that it is marked as credit note.
        self._assert_node_values(
            root,
            'cbc:InvoiceTypeCode',
            '02',
            attributes={'listVersionID': '1.1'},
        )
        # Ensure that the UUID of the origin invoice is present
        self._assert_node_values(
            root,
            'cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID',
            invoice_document.name,
        )
        self._assert_node_values(
            root,
            'cac:BillingReference/cac:InvoiceDocumentReference/cbc:UUID',
            invoice_document.myinvois_external_uuid,
        )

        with file_open('l10n_my_edi/tests/expected_xmls/credit_note.xml', 'rb') as f:
            expected_xml = etree.fromstring(f.read())
        self.assertXmlTreeEqual(root, expected_xml)

    def test_05_invoice_with_so(self):
        """
        Ensure that an invoice linked to an SO will not contain this information in the xml.
        """
        if self.env.ref('base.module_sale').state != 'installed':
            self.skipTest("This test requires the sale module to be installed.")

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'product_uom_qty': 1,
                'price_unit': 100,
                'currency_id': self.other_currency.id,
                'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
            })],
        }).sudo(False)
        sale_order.action_confirm()

        payment = self.env['sale.advance.payment.inv'].with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }).sudo().create({
            'advance_payment_method': 'delivered'
        }).sudo(False)
        payment.create_invoices()
        invoice = sale_order.invoice_ids[0]
        invoice.action_post()
        myinvois_document = invoice._create_myinvois_document()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)

        root = etree.fromstring(file)

        # Check the invoice type to endure that it is marked as credit note.
        node = root.xpath('cac:OrderReference', namespaces=NS_MAP)
        self.assertEqual(node, [])

        with file_open('l10n_my_edi/tests/expected_xmls/invoice_with_so.xml', 'rb') as f:
            expected_xml = etree.fromstring(f.read())
        self.assertXmlTreeEqual(root, expected_xml)

    def test_06_foreigner(self):
        """
        Check that the file is correct with a foreign customer.
        """
        invoice = self.init_invoice(
            'out_invoice', partner=self.partner_b, products=self.product_a, post=True,
        )
        myinvois_document = invoice._create_myinvois_document()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)

        root = etree.fromstring(file)
        customer_root = root.xpath('cac:AccountingCustomerParty/cac:Party', namespaces=NS_MAP)[0]

        # Party Identifications - TIN and BRN should be set.
        self._assert_node_values(
            customer_root,
            'cac:PartyIdentification/cbc:ID[@schemeID="TIN"]',
            self.partner_b.commercial_partner_id.vat,
        )
        self._assert_node_values(
            customer_root,
            'cac:PartyIdentification/cbc:ID[@schemeID="BRN"]',
            self.partner_b.commercial_partner_id.l10n_my_identification_number,
        )

        with file_open('l10n_my_edi/tests/expected_xmls/invoice_foreigner.xml', 'rb') as f:
            expected_xml = etree.fromstring(f.read())
        self.assertXmlTreeEqual(root, expected_xml)

    def test_07_tax_exempt(self):
        """
        Check that the file is correct with an exempt tax.
        """
        exempt_tax = self.env['account.tax'].create({
            'name': 'Tax Exempt',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 0,
            'l10n_my_tax_type': 'E',
        })
        invoice = self.init_invoice(
            'out_invoice', partner=self.partner_b, products=self.product_a, taxes=exempt_tax, post=True,
        )
        invoice.l10n_my_edi_exemption_reason = "Exempt Customer"
        myinvois_document = invoice._create_myinvois_document()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)

        root = etree.fromstring(file)
        # The tax exemption info should be on the line.
        item_root = root.xpath('cac:InvoiceLine/cac:Item', namespaces=NS_MAP)[0]
        self._assert_node_values(
            item_root,
            'cac:ClassifiedTaxCategory/cbc:Name',
            invoice.l10n_my_edi_exemption_reason,
        )
        self._assert_node_values(
            item_root,
            'cac:ClassifiedTaxCategory/cbc:TaxExemptionReason',
            invoice.l10n_my_edi_exemption_reason,
        )
        # And also on the tax total
        tax_subtotal_root = root.xpath('cac:TaxTotal/cac:TaxSubtotal', namespaces=NS_MAP)[0]
        self._assert_node_values(
            tax_subtotal_root,
            'cac:TaxCategory/cbc:Name',
            invoice.l10n_my_edi_exemption_reason,
        )
        self._assert_node_values(
            tax_subtotal_root,
            'cac:TaxCategory/cbc:TaxExemptionReason',
            invoice.l10n_my_edi_exemption_reason,
        )

        with file_open('l10n_my_edi/tests/expected_xmls/invoice_tax_exempt.xml', 'rb') as f:
            expected_xml = etree.fromstring(f.read())
        self.assertXmlTreeEqual(root, expected_xml)

    def test_08_self_billing(self):
        bill = self.init_invoice(
            'in_invoice', partner=self.partner_b, products=self.product_a, taxes=self.purchase_tax, post=True
        )
        myinvois_document = bill._create_myinvois_document()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)

        root = etree.fromstring(file)
        # We assert that the supplier is the partner of the invoice, with all information present.
        supplier_root = root.xpath('cac:AccountingSupplierParty/cac:Party', namespaces=NS_MAP)[0]
        data_to_check = [
            ('cac:PartyIdentification/cbc:ID[@schemeID="TIN"]', 'EI00000000030'),  # The partner_b malaysian TIN is set to the customer one, and it will be transformed to supplier during submission
            ('cac:PartyIdentification/cbc:ID[@schemeID="BRN"]', self.partner_b.commercial_partner_id.l10n_my_identification_number),
            ('cbc:IndustryClassificationCode', self.partner_b.commercial_partner_id.l10n_my_edi_industrial_classification.code),  # It should use the code on the partner.
            ('cac:PartyName/cbc:Name', self.partner_b.name),
        ]
        for path, expected_value in data_to_check:
            self._assert_node_values(supplier_root, path, expected_value)
        # And that the customer is the company.
        customer_root = root.xpath('cac:AccountingCustomerParty/cac:Party', namespaces=NS_MAP)[0]
        data_to_check = [
            ('cac:PartyIdentification/cbc:ID[@schemeID="TIN"]', self.company_data['company'].vat),  # We didn't set the new field as the company is malaysian, the vat should be in use.
            ('cac:PartyIdentification/cbc:ID[@schemeID="BRN"]', self.company_data['company'].l10n_my_identification_number),
            ('cac:PartyName/cbc:Name', self.company_data['company'].name),
        ]
        for path, expected_value in data_to_check:
            self._assert_node_values(customer_root, path, expected_value)

        with file_open('l10n_my_edi/tests/expected_xmls/invoice_self_billing.xml', 'rb') as f:
            expected_xml = etree.fromstring(f.read())
        self.assertXmlTreeEqual(root, expected_xml)

    def test_09_refund_note(self):
        """ A refund note is issued when an invoice has received a credit note, and that credit note was paid to the customer. """
        # Create the original invoice, and receive the payment.
        invoice = self.init_invoice(
            'out_invoice', partner=self.partner_b, products=self.product_a, post=True,
        )
        invoice_document = invoice._create_myinvois_document()
        # Simulate that the document was sent
        invoice_document.write({
            'myinvois_state': 'valid',
            'myinvois_external_uuid': '12345678912345678912345678',
        })
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': '2019-01-02',
        })._create_payments()
        # Create the credit note, and pay it back.
        action = invoice.action_reverse()
        reversal_wizard = self.env[action['res_model']].with_context(
            active_ids=invoice.ids,
            active_model='account.move',
            default_journal_id=invoice.journal_id.id,
        ).create({})
        action = reversal_wizard.reverse_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_note.action_post()
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=credit_note.ids).create({
            'payment_date': '2019-01-02',
        })._create_payments()
        # Generate the file and assert the type, should be "refund" (04)
        myinvois_document = credit_note._create_myinvois_document()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)

        root = etree.fromstring(file)
        self._assert_node_values(
            root,
            'cbc:InvoiceTypeCode',
            '04',
            attributes={'listVersionID': '1.1'},
        )

        with file_open('l10n_my_edi/tests/expected_xmls/refund_note_company_currency.xml', 'rb') as f:
            expected_xml = etree.fromstring(f.read())
        self.assertXmlTreeEqual(root, expected_xml)

    def test_10_credit_note(self):
        """ A credit note is issued when an invoice has received a credit note, and that credit note was not paid to the customer. """
        # Create the original invoice, don't receive a payment.
        invoice = self.init_invoice(
            'out_invoice', partner=self.partner_b, products=self.product_a, post=True,
        )
        invoice_document = invoice._create_myinvois_document()
        # Simulate that the document was sent
        invoice_document.write({
            'myinvois_state': 'valid',
            'myinvois_external_uuid': '12345678912345678912345678',
        })
        # Create the credit note to reduce the amount due of the invoice
        action = invoice.action_reverse()
        reversal_wizard = self.env[action['res_model']].with_context(
            active_ids=invoice.ids,
            active_model='account.move',
            default_journal_id=invoice.journal_id.id,
        ).create({})
        action = reversal_wizard.reverse_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        with Form(credit_note) as credit_note_form:
            with credit_note_form.invoice_line_ids.edit(0) as line:
                line.price_unit = 500
        credit_note.action_post()
        # Generate the file and assert the type, should be "credit note" (03)
        myinvois_document = credit_note._create_myinvois_document()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)

        root = etree.fromstring(file)
        self._assert_node_values(
            root,
            'cbc:InvoiceTypeCode',
            '02',
            attributes={'listVersionID': '1.1'},
        )

        with file_open('l10n_my_edi/tests/expected_xmls/credit_note_company_currency.xml', 'rb') as f:
            expected_xml = etree.fromstring(f.read())
        self.assertXmlTreeEqual(root, expected_xml)

    def test_11_bill_imports_form(self):
        """
        Ensure that when a bill contains a customs number; it is treated as an importation and not exportation.
        """
        exempt_tax = self.env['account.tax'].create({
            'name': 'Tax Exempt',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 0,
            'l10n_my_tax_type': 'E',
        })
        bill = self.init_invoice(
            'in_invoice', products=self.product_a, taxes=exempt_tax, post=True,
        )
        bill.write({
            'l10n_my_edi_exemption_reason': 'Exempt Customer',
            'l10n_my_edi_custom_form_reference': 'E12345678912',
        })
        myinvois_document = bill._create_myinvois_document()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)

        root = etree.fromstring(file)

        self._assert_node_values(
            root,
            'cac:AdditionalDocumentReference[descendant::*[local-name() = "DocumentType"]]/cbc:DocumentType',
            'CustomsImportForm',
        )

        with file_open('l10n_my_edi/tests/expected_xmls/bill_import.xml', 'rb') as f:
            expected_xml = etree.fromstring(f.read())
        self.assertXmlTreeEqual(root, expected_xml)

    def test_12_partner_ref_not_in_party_id(self):
        """
        Ensure that when an invoice contains a customs number; it is treated as an importation and not exportation.
        """
        invoice = self.init_invoice(
            'out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True
        )
        myinvois_document = invoice._create_myinvois_document()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)

        root = etree.fromstring(file)

        # There should not be any ID without attribute
        customer_root = root.xpath('cac:AccountingCustomerParty/cac:Party', namespaces=NS_MAP)[0]
        node = customer_root.xpath('cac:PartyIdentification/cbc:ID[count(@*)=0]', namespaces=NS_MAP)
        self.assertEqual(node, [])

        with file_open('l10n_my_edi/tests/expected_xmls/invoice_import.xml', 'rb') as f:
            expected_xml = etree.fromstring(f.read())
        self.assertXmlTreeEqual(root, expected_xml)

    def test_13_prepaid_amount_present(self):
        """
        Ensure the prepaid amount is present in the UBL XML under <cac:PrepaidPayment>
        """
        invoice = self.init_invoice('out_invoice', currency=self.other_currency, taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True)
        myinvois_document = invoice._create_myinvois_document()

        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': 2200.00, 'payment_date': '2024-07-15'
        })._create_payments()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)
        root = etree.fromstring(file)
        self._assert_node_values(
            root,
            'cac:PrepaidPayment/cbc:PaidAmount',
            '2200.00',
            attributes={'currencyID': self.other_currency.name}
        )

    def test_14_prioritize_invoice_line_classification_code(self):
        """
        Check if the classification code of invoice line is prioritized over the classification code of product
        when the two codes differ.
        """
        invoice = self.init_invoice(
            'out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a,
        )
        invoice.line_ids[0].write({
            'l10n_my_edi_classification_code': '002',
        })
        invoice.action_post()
        myinvois_document = invoice._create_myinvois_document()

        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)

        root = etree.fromstring(file)
        class_root = root.xpath('cac:InvoiceLine/cac:Item/cac:CommodityClassification', namespaces=NS_MAP)[0]

        self._assert_node_values(
            class_root,
            'cbc:ItemClassificationCode[@listID="CLASS"]',
            invoice.line_ids[0].l10n_my_edi_classification_code,
        )

    def test_15_none_tax(self):
        invoice = self.init_invoice(
            'out_invoice',
            partner=self.partner_b,
            products=self.product_a,
            post=False,
        )
        invoice.invoice_line_ids.write({'tax_ids': [Command.clear()]})  # remove existing taxes
        invoice.action_post()
        myinvois_document = invoice._create_myinvois_document()
        with self.assertRaises(UserError):
            myinvois_document.action_generate_xml_file()

    def _assert_node_values(self, root, node_path, text, attributes=None):
        node = root.xpath(node_path, namespaces=NS_MAP)

        assert node, f'The requested node has not been found: {node_path}'

        # Ensure that we don't have duplicated nodes. As of writing, all tested nodes are expected to exist only once in the result.
        node = root.xpath(node_path, namespaces=NS_MAP)
        self.assertEqual(len(node), 1, f"The node {node[0].tag} has been found {len(node)} time in the file")

        self.assertEqual(
            node[0].text,
            text,
        )
        if attributes:
            for attribute, value in attributes.items():
                self.assertEqual(
                    node[0].attrib[attribute],
                    value,
                )
