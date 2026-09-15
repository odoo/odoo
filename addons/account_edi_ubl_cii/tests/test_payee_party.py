# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import Command
from odoo.addons.account_edi_ubl_cii.tests.common import TestUblCiiCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'account_edi_payee')
class TestAccountEdiPayeeParty(TestUblCiiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payee = cls.env['res.partner'].create({
            'name': 'Factor Corp',
            'is_company': True,
            'vat': 'FR23334175221',
            'company_registry': '334175221',
        })
        cls.company_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'BE68539007547034',
            'partner_id': cls.company_data['company'].partner_id.id,
            'acc_holder_partner_id': cls.payee.id,
            'acc_holder_name': 'Factor Corp',
            'payment_note': 'Payment to factor',
            'allow_out_payment': True,
        })

    def test_ubl_bis3_payee_party_export(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_be.id,
            'partner_bank_id': self.company_bank.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product',
                'quantity': 1,
                'price_unit': 100,
                'tax_ids': [],
            })],
        })
        invoice.action_post()
        xml_content = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0]
        xml_tree = etree.fromstring(xml_content)
        namespaces = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }
        payee_name = xml_tree.find('.//cac:PayeeParty/cac:PartyName/cbc:Name', namespaces)
        self.assertIsNotNone(payee_name)
        self.assertEqual(payee_name.text, 'Factor Corp')
        instruction_note = xml_tree.find('.//cac:PaymentMeans/cbc:InstructionNote', namespaces)
        self.assertEqual(instruction_note.text, 'Payment to factor')

    def test_cii_payee_trade_party_export(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_be.id,
            'partner_bank_id': self.company_bank.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product',
                'quantity': 1,
                'price_unit': 100,
                'tax_ids': [],
            })],
        })
        invoice.action_post()
        xml_content = self.env['account.edi.xml.cii']._export_invoice(invoice)[0]
        xml_tree = etree.fromstring(xml_content)
        namespaces = {
            'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100',
        }
        payee_name = xml_tree.find('.//ram:PayeeTradeParty/ram:Name', namespaces)
        self.assertIsNotNone(payee_name)
        self.assertEqual(payee_name.text, 'Factor Corp')

    def test_ubl_bis3_factoring_export(self):
        self.company_bank.is_factoring = True
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_be.id,
            'partner_bank_id': self.company_bank.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product',
                'quantity': 1,
                'price_unit': 100,
                'tax_ids': [],
            })],
        })
        invoice.action_post()
        xml_content = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0]
        xml_tree = etree.fromstring(xml_content)
        namespaces = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }
        self.assertEqual(xml_tree.findtext('./cbc:InvoiceTypeCode', namespaces=namespaces), '393')
        self.assertEqual(
            xml_tree.findtext('./cac:PayeeParty/cbc:IndustryClassificationCode', namespaces=namespaces),
            'DL',
        )

    def test_cii_factoring_export(self):
        self.company_bank.is_factoring = True
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_be.id,
            'partner_bank_id': self.company_bank.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product',
                'quantity': 1,
                'price_unit': 100,
                'tax_ids': [],
            })],
        })
        invoice.action_post()
        xml_content = self.env['account.edi.xml.cii']._export_invoice(invoice)[0]
        xml_tree = etree.fromstring(xml_content)
        namespaces = {
            'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100',
            'rsm': 'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100',
        }
        self.assertEqual(
            xml_tree.findtext('./rsm:ExchangedDocument/ram:TypeCode', namespaces=namespaces),
            '393',
        )
        self.assertEqual(
            xml_tree.findtext('.//ram:PayeeTradeParty/ram:RoleCode', namespaces=namespaces),
            'DL',
        )

    def test_bt85_fallback_on_partner_name(self):
        bank = self.env['res.partner.bank'].create({
            'acc_number': 'BE68539007547035',
            'partner_id': self.company_data['company'].partner_id.id,
            'acc_holder_partner_id': self.payee.id,
            'allow_out_payment': True,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_be.id,
            'partner_bank_id': bank.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product',
                'quantity': 1,
                'price_unit': 100,
                'tax_ids': [],
            })],
        })
        invoice.action_post()
        xml_content = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0]
        xml_tree = etree.fromstring(xml_content)
        namespaces = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }
        self.assertEqual(
            xml_tree.findtext('.//cac:PayeeParty/cac:PartyName/cbc:Name', namespaces=namespaces),
            'Factor Corp',
        )
        self.assertEqual(
            xml_tree.findtext('.//cac:PaymentMeans/cac:PayeeFinancialAccount/cbc:Name', namespaces=namespaces),
            'Factor Corp',
        )

    def test_ubl_import_enriches_vendor_bank_factoring_with_siret(self):
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0</cbc:CustomizationID>
    <cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>
    <cbc:ID>INV/FACT/00001</cbc:ID>
    <cbc:IssueDate>2026-02-01</cbc:IssueDate>
    <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
    <cbc:InvoiceTypeCode>393</cbc:InvoiceTypeCode>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyName><cbc:Name>Vendor FR</cbc:Name></cac:PartyName>
            <cac:PostalAddress><cac:Country><cbc:IdentificationCode>BE</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
            <cac:PartyTaxScheme>
                <cbc:CompanyID>BE0477472701</cbc:CompanyID>
                <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>Vendor FR</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PartyName><cbc:Name>My company</cbc:Name></cac:PartyName>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:PayeeParty>
        <cbc:IndustryClassificationCode>DL</cbc:IndustryClassificationCode>
        <cac:PartyName><cbc:Name>Affactureur Import</cbc:Name></cac:PartyName>
        <cac:PartyLegalEntity>
            <cbc:RegistrationName>Affactureur Import</cbc:RegistrationName>
            <cbc:CompanyID schemeID="0002">818620783</cbc:CompanyID>
        </cac:PartyLegalEntity>
        <cac:PartyIdentification>
            <cbc:ID schemeID="0009">81862078300048</cbc:ID>
        </cac:PartyIdentification>
    </cac:PayeeParty>
    <cac:PaymentMeans>
        <cac:PayeeFinancialAccount>
            <cbc:ID>FR7630001007941234567890185</cbc:ID>
            <cbc:Name>Affactureur Import</cbc:Name>
        </cac:PayeeFinancialAccount>
    </cac:PaymentMeans>
    <cac:TaxTotal><cbc:TaxAmount currencyID="EUR">0</cbc:TaxAmount></cac:TaxTotal>
    <cac:LegalMonetaryTotal>
        <cbc:TaxExclusiveAmount currencyID="EUR">100</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="EUR">100</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="EUR">100</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    <cac:InvoiceLine>
        <cbc:ID>1</cbc:ID>
        <cbc:InvoicedQuantity unitCode="C62">1</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="EUR">100</cbc:LineExtensionAmount>
        <cac:Item><cbc:Name>Service</cbc:Name></cac:Item>
        <cac:Price><cbc:PriceAmount currencyID="EUR">100</cbc:PriceAmount></cac:Price>
    </cac:InvoiceLine>
</Invoice>"""
        xml_attachment = self.env['ir.attachment'].create({
            'mimetype': 'application/xml',
            'name': 'factoring_import.xml',
            'raw': xml_content,
        })
        invoice = self._import_invoice_as_attachment_on(
            attachment=xml_attachment,
            journal=self.company_data['default_journal_purchase'],
        )
        bank = invoice.partner_bank_id
        self.assertTrue(bank)
        self.assertTrue(bank.is_factoring)
        self.assertEqual(bank.acc_holder_name, 'Affactureur Import')
        self.assertEqual(bank.acc_holder_partner_id.name, 'Affactureur Import')
        if 'siret' in bank.acc_holder_partner_id._fields:
            self.assertEqual(bank.acc_holder_partner_id.siret, '81862078300048')

    def test_cii_factoring_payee_exports_siret_and_vat(self):
        if 'siret' not in self.env['res.partner']._fields:
            self.skipTest('Partner siret field required (install l10n_fr)')
        payee_vals = {
            'name': 'Affactureur Export FR',
            'is_company': True,
            'vat': 'FR65818620783',
            'siret': '81862078300048',
        }
        if 'siren' in self.env['res.partner']._fields:
            payee_vals['siren'] = '818620783'
        if 'nic' in self.env['res.partner']._fields:
            payee_vals['nic'] = '00048'
        payee = self.env['res.partner'].create(payee_vals)
        company_bank = self.env['res.partner.bank'].create({
            'acc_number': 'FR7630001007941234567890185',
            'partner_id': self.company_data['company'].partner_id.id,
            'acc_holder_partner_id': payee.id,
            'acc_holder_name': 'Affactureur Export FR',
            'is_factoring': True,
            'allow_out_payment': True,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_be.id,
            'partner_bank_id': company_bank.id,
            'invoice_line_ids': [Command.create({
                'name': 'Service',
                'quantity': 1,
                'price_unit': 100,
                'tax_ids': [],
            })],
        })
        invoice.action_post()
        xml_content = self.env['account.edi.xml.cii']._export_invoice(invoice)[0]
        xml_tree = etree.fromstring(xml_content)
        namespaces = {
            'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100',
            'rsm': 'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100',
        }
        payee_party = xml_tree.find('.//ram:PayeeTradeParty', namespaces)
        self.assertIsNotNone(payee_party)
        self.assertEqual(
            payee_party.findtext('./ram:RegisteredID[@schemeID="0009"]', namespaces=namespaces),
            '81862078300048',
        )
        self.assertEqual(
            payee_party.findtext('./ram:SpecifiedLegalOrganization/ram:ID', namespaces=namespaces),
            '818620783',
        )
        self.assertEqual(
            payee_party.findtext('./ram:SpecifiedTaxRegistration/ram:ID', namespaces=namespaces),
            'FR65818620783',
        )
        self.assertEqual(
            xml_tree.findtext('./rsm:ExchangedDocument/ram:TypeCode', namespaces=namespaces),
            '393',
        )
        self.assertEqual(
            payee_party.findtext('./ram:RoleCode', namespaces=namespaces),
            'DL',
        )

    def test_ubl_bis3_payee_exports_siret(self):
        if 'siret' not in self.env['res.partner']._fields:
            self.skipTest('Partner siret field required (install l10n_fr)')
        payee = self.env['res.partner'].create({
            'name': 'Affactureur Export FR',
            'is_company': True,
            'vat': 'FR65818620783',
            'siret': '81862078300048',
        })
        bank = self.env['res.partner.bank'].create({
            'acc_number': 'FR7630001007941234567890185',
            'partner_id': self.company_data['company'].partner_id.id,
            'acc_holder_partner_id': payee.id,
            'allow_out_payment': True,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_be.id,
            'partner_bank_id': bank.id,
            'invoice_line_ids': [Command.create({
                'name': 'Service',
                'quantity': 1,
                'price_unit': 100,
                'tax_ids': [],
            })],
        })
        invoice.action_post()
        xml_content = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0]
        xml_tree = etree.fromstring(xml_content)
        namespaces = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }
        self.assertEqual(
            xml_tree.findtext(
                './/cac:PayeeParty/cac:PartyIdentification/cbc:ID[@schemeID="0009"]',
                namespaces=namespaces,
            ),
            '81862078300048',
        )
