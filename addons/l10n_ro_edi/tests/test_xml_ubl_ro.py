import datetime
import json
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import (
    TestUBLCommon,
)


def _patch_SPV_return_values(session, company, endpoint, method, params, data=None):
    if endpoint == 'listaMesajeFactura':
        content = {
            'mesaje': [
                {   # Existing invoice
                    'data_creare': '202503271639',
                    'cif': company.vat,
                    'id_solicitare': '5019882651',
                    'detalii': f"Factura cu id_incarcare=5019882651 emisa de cif_emitent={company.vat} pentru cif_beneficiar=RO1234567897",
                    'tip': 'FACTURA TRIMISA',
                    'id': '3029027561',
                },
                {   # New Bill
                    'data_creare': '202504011105',
                    'cif': company.vat,
                    'id_solicitare': '5020286927',
                    'detalii': f"Factura cu id_incarcare=5020286927 emisa de cif_emitent={company.vat} pentru cif_beneficiar=RO1234567897",
                    'tip': 'FACTURA PRIMITA',
                    'id': '3029811017',
                },
                {   # Error with invoice
                    'data_creare': '202504081504',
                    'cif': company.vat,
                    'id_solicitare': '5020592384',
                    'detalii': 'Erori de validare identificate la factura transmisa cu id_incarcare=5020592384',
                    'tip': 'ERORI FACTURA',
                    'id': '3030159318',
                },
            ],
        }
        content = json.dumps(content).encode()

    elif endpoint == 'descarcare':
        invoice_data = {
            '5019882651': {
                'error': '',
                'signature': {
                    'attachment_raw': b'<?xml version=\'1.0\' encoding=\'UTF-8\'?><Signature xmlns="http://www.w3.org/2000/09/xmldsig#"><SignedInfo><CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/><SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/><Reference URI=""><DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/><DigestValue>__ignore__</DigestValue></Reference></SignedInfo><SignatureValue>KEY_SIG_1</SignatureValue><KeyInfo><X509Data><X509SubjectName>1.2.840.113549.1.9.1=#160f636f6e7461637440616e61662e726f,CN=ANAF TEST,OU=ANAF-TEST,O=ANAF-TEST,L=Bucharest,ST=Bucharest,C=RO</X509SubjectName><X509Certificate>KEY_CERT_1</X509Certificate></X509Data></KeyInfo></Signature>',
                    'key_signature': 'KEY_SIG_1',
                    'key_certificate': 'KEY_CERT_1',
                },
                'invoice': {
                    'name': 'INV/2025/00002',
                    'amount_total': '1190.00',
                    'due_date': datetime.date(2025, 3, 27),
                    'invoice_raw': b'<?xml version=\'1.0\' encoding=\'UTF-8\'?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"><cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1</cbc:CustomizationID><cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID><cbc:ID>INV/2025/00002</cbc:ID><cbc:IssueDate>2025-03-27</cbc:IssueDate><cbc:DueDate>2025-03-27</cbc:DueDate><cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode><cbc:DocumentCurrencyCode>RON</cbc:DocumentCurrencyCode><cbc:TaxCurrencyCode>RON</cbc:TaxCurrencyCode><cac:OrderReference><cbc:ID>INV/2025/00002</cbc:ID></cac:OrderReference><cac:AdditionalDocumentReference><cbc:ID>INV_2025_00002.pdf</cbc:ID><cac:Attachment><cbc:EmbeddedDocumentBinaryObject mimeCode="application/pdf" filename="INV_2025_00002.pdf">__ignore__</cbc:EmbeddedDocumentBinaryObject></cac:Attachment></cac:AdditionalDocumentReference><cac:AccountingSupplierParty><cac:Party><cbc:EndpointID schemeID="9947">23422586</cbc:EndpointID><cac:PartyName><cbc:Name>My Company</cbc:Name></cac:PartyName><cac:PostalAddress><cbc:StreetName>a normal ro streetname and nb</cbc:StreetName><cbc:CityName>ro city</cbc:CityName><cbc:PostalZone>54321</cbc:PostalZone><cbc:CountrySubentity>RO-AB</cbc:CountrySubentity><cac:Country><cbc:IdentificationCode>RO</cbc:IdentificationCode></cac:Country></cac:PostalAddress><cac:PartyTaxScheme><cbc:CompanyID>23422586</cbc:CompanyID><cac:TaxScheme><cbc:ID>NOT_EU_VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme><cac:PartyLegalEntity><cbc:RegistrationName>My Company</cbc:RegistrationName><cbc:CompanyID>23422586</cbc:CompanyID></cac:PartyLegalEntity><cac:Contact><cbc:Name>My Company</cbc:Name></cac:Contact></cac:Party></cac:AccountingSupplierParty><cac:AccountingCustomerParty><cac:Party><cbc:EndpointID schemeID="9947">30678383</cbc:EndpointID><cac:PartyName><cbc:Name>TEST B2C</cbc:Name></cac:PartyName><cac:PostalAddress><cbc:StreetName>Another normal RO street name</cbc:StreetName><cbc:CityName>Sclayn</cbc:CityName><cbc:PostalZone>54322</cbc:PostalZone><cbc:CountrySubentity>RO-AB</cbc:CountrySubentity><cac:Country><cbc:IdentificationCode>RO</cbc:IdentificationCode></cac:Country></cac:PostalAddress><cac:PartyTaxScheme><cbc:CompanyID>30678383</cbc:CompanyID><cac:TaxScheme><cbc:ID>NOT_EU_VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme><cac:PartyLegalEntity><cbc:RegistrationName>TEST B2C</cbc:RegistrationName><cbc:CompanyID>30678383</cbc:CompanyID></cac:PartyLegalEntity><cac:Contact><cbc:Name>TEST B2C</cbc:Name><cbc:ElectronicMail>test_b2c@test.com</cbc:ElectronicMail></cac:Contact></cac:Party></cac:AccountingCustomerParty><cac:Delivery><cac:DeliveryLocation><cac:Address><cbc:StreetName></cbc:StreetName><cbc:CityName></cbc:CityName><cbc:PostalZone></cbc:PostalZone><cbc:CountrySubentity>RO-AB</cbc:CountrySubentity><cac:Country><cbc:IdentificationCode>RO</cbc:IdentificationCode></cac:Country></cac:Address></cac:DeliveryLocation></cac:Delivery><cac:PaymentMeans><cbc:PaymentMeansCode name="credit transfer">30</cbc:PaymentMeansCode><cbc:PaymentID>INV/2025/00002</cbc:PaymentID><cac:PayeeFinancialAccount><cbc:ID>RO49AAAA1B31007593840000</cbc:ID></cac:PayeeFinancialAccount></cac:PaymentMeans><cac:TaxTotal><cbc:TaxAmount currencyID="RON">190.00</cbc:TaxAmount><cac:TaxSubtotal><cbc:TaxableAmount currencyID="RON">1000.00</cbc:TaxableAmount><cbc:TaxAmount currencyID="RON">190.00</cbc:TaxAmount><cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>19.0</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory></cac:TaxSubtotal></cac:TaxTotal><cac:LegalMonetaryTotal><cbc:LineExtensionAmount currencyID="RON">1000.00</cbc:LineExtensionAmount><cbc:TaxExclusiveAmount currencyID="RON">1000.00</cbc:TaxExclusiveAmount><cbc:TaxInclusiveAmount currencyID="RON">1190.00</cbc:TaxInclusiveAmount><cbc:PrepaidAmount currencyID="RON">0.00</cbc:PrepaidAmount><cbc:PayableAmount currencyID="RON">1190.00</cbc:PayableAmount></cac:LegalMonetaryTotal><cac:InvoiceLine><cbc:ID>1</cbc:ID><cbc:InvoicedQuantity unitCode="C62">1.0</cbc:InvoicedQuantity><cbc:LineExtensionAmount currencyID="RON">1000.00</cbc:LineExtensionAmount><cac:Item><cbc:Description>A</cbc:Description><cbc:Name>A</cbc:Name><cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>19.0</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory></cac:Item><cac:Price><cbc:PriceAmount currencyID="RON">1000.0</cbc:PriceAmount></cac:Price></cac:InvoiceLine></Invoice>'
                },
            },
            '5020592384': {
                'error': '[BR-CO-09]-The Seller VAT identifier (BT-31), the Seller tax representative VAT identifier (BT-63) and the Buyer VAT identifier (BT-48) shall have a prefix in accordance with ISO code ISO 3166-1 alpha-2 by which the country of issue may be identified. Nevertheless, Greece may use the prefix ‘EL’.',
                'signature': {},
                'invoice': {},
            }
        }
        content = invoice_data.get(data['download_id'], {})
    return {'content': content}


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLRO(TestUBLCommon):

    @classmethod
    @TestUBLCommon.setup_country('ro')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.ro').id,  # needed to compute peppol_endpoint based on VAT
            'state_id': cls.env.ref('base.RO_B').id,
            'name': 'Hudson Construction',
            'city': 'SECTOR1',
            'zip': '010101',
            'vat': 'RO1234567897',
            'phone': '+40 123 456 789',
            'street': "Strada Kunst, 3",
        })

        cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.company_data['company'].partner_id.id,
            'acc_number': 'RO98RNCB1234567890123456',
        })

        cls.partner_a = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.ro').id,
            'state_id': cls.env.ref('base.RO_B').id,
            'name': 'Roasted Romanian Roller',
            'city': 'SECTOR3',
            'zip': '010101',
            'vat': 'RO1234567897',
            'phone': '+40 123 456 780',
            'street': "Rolling Roast, 88",
            'bank_ids': [(0, 0, {'acc_number': 'RO98RNCB1234567890123456'})],
            'ref': 'ref_partner_a',
            'invoice_edi_format': 'ciusro',
        })

        cls.tax_19 = cls.env['account.tax'].create({
            'name': 'tax_19',
            'amount_type': 'percent',
            'amount': 19,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.ro').id,
        })

    ####################################################
    # Test export - import
    ####################################################

    def create_move(self, move_type, send=True, **kwargs):
        return self._generate_move(
            self.env.company.partner_id,
            self.partner_a,
            send=send,
            move_type=move_type,
            invoice_line_ids=[
                {
                    'name': 'Test Product A',
                    'product_id': self.product_a.id,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                },
                {
                    'name': 'Test Product B',
                    'product_id': self.product_b.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                },
            ],
            **kwargs
        )

    def get_attachment(self, move):
        self.assertTrue(move.ubl_cii_xml_id)
        self.assertEqual(move.ubl_cii_xml_id.name[-11:], "cius_ro.xml")
        return move.ubl_cii_xml_id

    def test_export_invoice(self):
        invoice = self.create_move("out_invoice", currency_id=self.company.currency_id.id)
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice.xml')

    def test_export_credit_note(self):
        refund = self.create_move("out_refund", currency_id=self.company.currency_id.id)
        attachment = self.get_attachment(refund)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_refund.xml')

    def test_export_invoice_different_currency(self):
        invoice = self.create_move("out_invoice")
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice_different_currency.xml')

    def test_export_invoice_without_country_code_prefix_in_vat(self):
        self.company_data['company'].write({'vat': '1234567897'})
        self.partner_a.write({'vat': False})
        invoice = self.create_move("out_invoice", currency_id=self.company.currency_id.id)
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice_no_prefix_vat.xml')

    def test_export_no_vat_but_have_company_registry(self):
        self.company_data['company'].write({'vat': False, 'company_registry': 'RO1234567897'})
        invoice = self.create_move("out_invoice", currency_id=self.company.currency_id.id)
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice.xml')

    def test_export_no_vat_but_have_company_registry_without_prefix(self):
        self.company_data['company'].write({'vat': False, 'company_registry': '1234567897'})
        self.partner_a.write({'vat': False})
        invoice = self.create_move("out_invoice", currency_id=self.company.currency_id.id)
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice_no_prefix_vat.xml')

    def test_export_no_vat_and_no_company_registry_raises_error(self):
        self.company_data['company'].write({'vat': False, 'company_registry': False})
        invoice = self.create_move("out_invoice", send=False)
        with self.assertRaisesRegex(UserError, "doesn't have a VAT nor Company ID"):
            invoice._generate_and_send(allow_fallback_pdf=False, template_id=self.move_template.id)

    def test_export_constraints(self):
        self.company_data['company'].company_registry = False
        for required_field in ('city', 'street', 'state_id', 'vat'):
            prev_val = self.company_data["company"][required_field]
            self.company_data["company"][required_field] = False
            invoice = self.create_move("out_invoice", send=False)
            with self.assertRaisesRegex(UserError, "required"):
                invoice._generate_and_send(allow_fallback_pdf=False, template_id=self.move_template.id)
            self.company_data["company"][required_field] = prev_val

        self.company_data["company"].city = "Bucharest"
        invoice = self.create_move("out_invoice", send=False)
        with self.assertRaisesRegex(UserError, "city name must be 'SECTORX'"):
            invoice._generate_and_send(allow_fallback_pdf=False, template_id=self.move_template.id)

    def test_test(self):
        with patch('odoo.addons.l10n_ro_edi.models.utils.make_efactura_request', new=_patch_SPV_return_values):
            results = self.env['account.move']._l10n_ro_edi_fetch_invoices()
            pass
