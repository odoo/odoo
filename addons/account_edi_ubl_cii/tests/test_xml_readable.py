# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from lxml import etree

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_preview import xml_tree_to_html
from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_reader import read_invoice
from odoo.exceptions import UserError
from odoo.tests import tagged

UBL_INVOICE = b'''<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>VIG/2026/00014</cbc:ID>
  <cbc:IssueDate>2026-10-02</cbc:IssueDate>
  <cbc:DueDate>2026-11-01</cbc:DueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:Note>#PMT#Indemnite forfaitaire de 40 EUR</cbc:Note>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty><cac:Party>
    <cac:PostalAddress>
      <cbc:StreetName>1 rue du Test</cbc:StreetName><cbc:CityName>Rennes</cbc:CityName>
      <cbc:PostalZone>35000</cbc:PostalZone><cac:Country><cbc:IdentificationCode>FR</cbc:IdentificationCode></cac:Country>
    </cac:PostalAddress>
    <cac:PartyTaxScheme><cbc:CompanyID>FR12931473060</cbc:CompanyID></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Fournisseur SAS</cbc:RegistrationName><cbc:CompanyID>931473060</cbc:CompanyID></cac:PartyLegalEntity>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party>
    <cac:PartyLegalEntity><cbc:RegistrationName>Client SARL</cbc:RegistrationName></cac:PartyLegalEntity>
  </cac:Party></cac:AccountingCustomerParty>
  <cac:PayeeParty><cac:PartyName><cbc:Name>Factor SA</cbc:Name></cac:PartyName>
    <cac:PostalAddress><cbc:StreetName>2 rue Affacturage</cbc:StreetName><cbc:CityName>Lyon</cbc:CityName>
      <cbc:PostalZone>69001</cbc:PostalZone><cac:Country><cbc:IdentificationCode>FR</cbc:IdentificationCode></cac:Country>
    </cac:PostalAddress>
  </cac:PayeeParty>
  <cac:Delivery><cac:DeliveryParty><cac:PartyName><cbc:Name>Entrepot Client</cbc:Name></cac:PartyName>
    <cac:PostalAddress><cbc:StreetName>9 quai de livraison</cbc:StreetName><cbc:CityName>Nantes</cbc:CityName>
      <cbc:PostalZone>44000</cbc:PostalZone><cac:Country><cbc:IdentificationCode>FR</cbc:IdentificationCode></cac:Country>
    </cac:PostalAddress>
  </cac:DeliveryParty></cac:Delivery>
  <cac:PaymentMeans>
    <cbc:PaymentMeansCode name="SEPA credit transfer">58</cbc:PaymentMeansCode>
    <cbc:PaymentID>REF-14</cbc:PaymentID>
    <cac:PayeeFinancialAccount><cbc:ID>FR7630001007941234567890185</cbc:ID></cac:PayeeFinancialAccount>
  </cac:PaymentMeans>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">20.00</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">20.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:Percent>20</cbc:Percent></cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">100.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">120.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="EUR">120.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="C62">2</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cac:Item><cbc:Name>Abonnement</cbc:Name><cac:ClassifiedTaxCategory><cbc:Percent>20</cbc:Percent></cac:ClassifiedTaxCategory></cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">50.00</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
</Invoice>'''

CII_INVOICE = b'''<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataTypes:100">
  <rsm:ExchangedDocument>
    <ram:ID>F-2026-7</ram:ID><ram:TypeCode>381</ram:TypeCode>
    <ram:IssueDateTime><udt:DateTimeString format="102">20261002</udt:DateTimeString></ram:IssueDateTime>
    <ram:IncludedNote><ram:Content>#PMD#Penalites de retard</ram:Content></ram:IncludedNote>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:IncludedSupplyChainTradeLineItem>
      <ram:SpecifiedTradeProduct><ram:Name>Hosting</ram:Name></ram:SpecifiedTradeProduct>
      <ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice><ram:ChargeAmount>10.00</ram:ChargeAmount></ram:NetPriceProductTradePrice></ram:SpecifiedLineTradeAgreement>
      <ram:SpecifiedLineTradeDelivery><ram:BilledQuantity unitCode="C62">3</ram:BilledQuantity></ram:SpecifiedLineTradeDelivery>
      <ram:SpecifiedLineTradeSettlement>
        <ram:ApplicableTradeTax><ram:RateApplicablePercent>20</ram:RateApplicablePercent></ram:ApplicableTradeTax>
        <ram:SpecifiedTradeSettlementLineMonetarySummation><ram:LineTotalAmount>30.00</ram:LineTotalAmount></ram:SpecifiedTradeSettlementLineMonetarySummation>
      </ram:SpecifiedLineTradeSettlement>
    </ram:IncludedSupplyChainTradeLineItem>
    <ram:ApplicableHeaderTradeAgreement>
      <ram:SellerTradeParty>
        <ram:Name>Hebergeur SAS</ram:Name>
        <ram:DefinedTradeContact>
          <ram:EmailURIUniversalCommunication><ram:URIID>seller@example.com</ram:URIID></ram:EmailURIUniversalCommunication>
        </ram:DefinedTradeContact>
        <ram:URIUniversalCommunication><ram:URIID schemeID="0225">315143296_11274</ram:URIID></ram:URIUniversalCommunication>
        <ram:SpecifiedLegalOrganization><ram:ID schemeID="0002">991192543</ram:ID></ram:SpecifiedLegalOrganization>
        <ram:PostalTradeAddress><ram:PostcodeCode>75001</ram:PostcodeCode><ram:CityName>Paris</ram:CityName><ram:CountryID>FR</ram:CountryID></ram:PostalTradeAddress>
        <ram:SpecifiedTaxRegistration><ram:ID schemeID="VA">FR12991192543</ram:ID></ram:SpecifiedTaxRegistration>
      </ram:SellerTradeParty>
      <ram:BuyerTradeParty><ram:Name>Client SARL</ram:Name></ram:BuyerTradeParty>
    </ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeDelivery>
      <ram:ShipToTradeParty>
        <ram:Name>Entrepot Client</ram:Name>
        <ram:PostalTradeAddress><ram:LineOne>9 quai de livraison</ram:LineOne><ram:PostcodeCode>44000</ram:PostcodeCode><ram:CityName>Nantes</ram:CityName><ram:CountryID>FR</ram:CountryID></ram:PostalTradeAddress>
      </ram:ShipToTradeParty>
    </ram:ApplicableHeaderTradeDelivery>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
      <ram:PaymentReference>REF-7</ram:PaymentReference>
      <ram:PayeeTradeParty><ram:Name>Factor SA</ram:Name></ram:PayeeTradeParty>
      <ram:SpecifiedTradeSettlementPaymentMeans>
        <ram:TypeCode>58</ram:TypeCode>
        <ram:PayeePartyCreditorFinancialAccount>
          <ram:IBANID>FR7630001007941234567890185</ram:IBANID>
          <ram:ProprietaryID>FR7630001007941234567890185</ram:ProprietaryID>
        </ram:PayeePartyCreditorFinancialAccount>
      </ram:SpecifiedTradeSettlementPaymentMeans>
      <ram:ApplicableTradeTax><ram:CalculatedAmount>6.00</ram:CalculatedAmount><ram:BasisAmount>30.00</ram:BasisAmount><ram:RateApplicablePercent>20</ram:RateApplicablePercent></ram:ApplicableTradeTax>
      <ram:SpecifiedTradePaymentTerms>
        <ram:Description>30 jours</ram:Description>
        <ram:DueDateDateTime><udt:DateTimeString format="102">20261101</udt:DateTimeString></ram:DueDateDateTime>
      </ram:SpecifiedTradePaymentTerms>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:LineTotalAmount>30.00</ram:LineTotalAmount><ram:TaxBasisTotalAmount>30.00</ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount currencyID="EUR">6.00</ram:TaxTotalAmount><ram:GrandTotalAmount>36.00</ram:GrandTotalAmount>
        <ram:DuePayableAmount>36.00</ram:DuePayableAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>'''

XSS_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<Doc>
  <Note>&lt;script&gt;alert(1)&lt;/script&gt;</Note>
</Doc>
'''

SECTION_ORDER = (
    'Issuer',
    'Invoiced party',
    'Delivery address',
    'Payee',
    'Payment',
    'Legal mentions',
)


@tagged('post_install', '-at_install')
class TestXmlReadable(AccountTestInvoicingCommon):

    def _make_move(self, xml_content, move_type='in_invoice'):
        move = self.init_invoice(move_type, products=self.product_a)
        attachment = self.env['ir.attachment'].create({
            'name': 'supplier.xml',
            'raw': xml_content,
            'mimetype': 'application/xml',
            'res_model': 'account.move',
            'res_id': move.id,
        })
        return move, attachment

    def _preview_notes(self, move):
        return move.message_ids.filtered(lambda message: 'account-xml-preview:' in (message.body or ''))

    def test_read_ubl_and_cii(self):
        ubl = read_invoice(etree.fromstring(UBL_INVOICE))
        self.assertEqual(ubl['syntax'], 'ubl')
        self.assertEqual(ubl['seller']['name'], 'Fournisseur SAS')
        self.assertEqual(ubl['delivery']['city'], 'Nantes')
        self.assertEqual(ubl['payee']['name'], 'Factor SA')
        self.assertEqual((ubl['payment_means_code'], ubl['payment_means_name']), ('58', 'SEPA credit transfer'))
        self.assertEqual(ubl['lines'][0]['name'], 'Abonnement')
        self.assertFalse(ubl['is_credit_note'])

        cii = read_invoice(etree.fromstring(CII_INVOICE))
        self.assertEqual(cii['syntax'], 'cii')
        self.assertTrue(cii['is_credit_note'])
        self.assertEqual(cii['seller']['email'], 'seller@example.com')
        self.assertEqual(cii['seller']['legal_id'], '991192543')
        self.assertNotIn('315143296', cii['seller']['email'])
        self.assertEqual(cii['issue_date'], '2026-10-02')
        self.assertEqual(len(cii['ibans']), 1)

        facturx = CII_INVOICE.replace(
            b'<rsm:ExchangedDocument>',
            b'<rsm:ExchangedDocumentContext><ram:GuidelineSpecifiedDocumentContextParameter>'
            b'<ram:ID>urn:factur-x.eu:1p0:basicwl</ram:ID>'
            b'</ram:GuidelineSpecifiedDocumentContextParameter></rsm:ExchangedDocumentContext>'
            b'<rsm:ExchangedDocument>',
            1,
        )
        self.assertEqual(read_invoice(etree.fromstring(facturx))['syntax'], 'facturx')
        self.assertFalse(read_invoice(None))
        self.assertFalse(read_invoice(etree.fromstring(b'<foo/>')))

    def test_preview_escapes_text_and_is_idempotent(self):
        html = str(xml_tree_to_html(etree.fromstring(XSS_XML), filename='x.xml', token='1-abc'))
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('account-xml-preview:1-abc', html)

        move, attachment = self._make_move(UBL_INVOICE)
        with patch.object(type(self.env['ir.actions.report']), '_run_wkhtmltopdf', return_value=b'%PDF-1.4 readable'):
            move._extend_with_attachments(attachment, new=True)
            move._extend_with_attachments(attachment, new=True)
        self.assertEqual(len(self._preview_notes(move)), 1)

    def test_readable_pdf_is_main_attachment_and_not_the_legal_pdf(self):
        move, attachment = self._make_move(UBL_INVOICE)
        with patch.object(type(self.env['ir.actions.report']), '_run_wkhtmltopdf', return_value=b'%PDF-1.4 readable'):
            move._extend_with_attachments(attachment, new=True)
        main = move.message_main_attachment_id
        self.assertTrue(main.name.endswith('_readable.pdf'))
        self.assertEqual(main.mimetype, 'application/pdf')
        self.assertEqual(main.raw, b'%PDF-1.4 readable')
        self.assertFalse(main.res_field)
        self.assertFalse(move.invoice_pdf_report_id)

    def test_supplier_pdf_already_main_is_kept(self):
        move, attachment = self._make_move(UBL_INVOICE)
        supplier_pdf = self.env['ir.attachment'].create({
            'name': 'cdiscount.pdf',
            'raw': b'%PDF-supplier',
            'mimetype': 'application/pdf',
            'res_model': 'account.move',
            'res_id': move.id,
        })
        move.message_main_attachment_id = supplier_pdf
        with patch.object(type(self.env['ir.actions.report']), '_run_wkhtmltopdf', return_value=b'%PDF-1.4 readable') as render:
            move._extend_with_attachments(attachment, new=True)
            render.assert_not_called()
        self.assertEqual(move.message_main_attachment_id, supplier_pdf)

    def test_supplier_pdf_not_yet_main_is_kept(self):
        """Journal upload sets the Factur-X PDF as main only after extend returns."""
        move, attachment = self._make_move(UBL_INVOICE)
        supplier_pdf = self.env['ir.attachment'].create({
            'name': 'factur-x.pdf',
            'raw': b'%PDF-supplier',
            'mimetype': 'application/pdf',
        })
        with patch.object(type(self.env['ir.actions.report']), '_run_wkhtmltopdf', return_value=b'%PDF-1.4 readable') as render:
            move._extend_with_attachments(attachment | supplier_pdf, new=True)
            render.assert_not_called()
        self.assertFalse(self.env['ir.attachment'].search_count([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', move.id),
            ('name', '=like', '%_readable.pdf'),
        ]))

    def test_manual_action_replaces_the_supplier_pdf(self):
        move, _attachment = self._make_move(UBL_INVOICE)
        supplier_pdf = self.env['ir.attachment'].create({
            'name': 'cdiscount.pdf',
            'raw': b'%PDF-supplier',
            'mimetype': 'application/pdf',
            'res_model': 'account.move',
            'res_id': move.id,
        })
        move.message_main_attachment_id = supplier_pdf
        with patch.object(type(self.env['ir.actions.report']), '_run_wkhtmltopdf', return_value=b'%PDF-1.4 readable'):
            action = move.action_generate_readable_pdf()
        self.assertEqual(action['res_id'], move.id)
        self.assertTrue(move.message_main_attachment_id.name.endswith('_readable.pdf'))
        self.assertTrue(supplier_pdf.exists())
        self.assertFalse(move.invoice_pdf_report_id)

    def test_manual_action_requires_an_xml(self):
        move = self.init_invoice('in_invoice', products=self.product_a)
        with self.assertRaises(UserError):
            move.action_generate_readable_pdf()

    def test_customer_invoice_is_previewed_but_not_replaced(self):
        move, attachment = self._make_move(UBL_INVOICE, move_type='out_invoice')
        with patch.object(type(self.env['ir.actions.report']), '_run_wkhtmltopdf', return_value=b'%PDF-1.4 readable') as render:
            move._extend_with_attachments(attachment, new=True)
            render.assert_not_called()
        self.assertEqual(len(self._preview_notes(move)), 1)
        self.assertFalse(move.message_main_attachment_id.name.endswith('_readable.pdf') if move.message_main_attachment_id else False)

    def test_html_block_order_comes_from_the_xml(self):
        for xml_content, seller, line_name in (
            (UBL_INVOICE, 'Fournisseur SAS', 'Abonnement'),
            (CII_INVOICE, 'Hebergeur SAS', 'Hosting'),
        ):
            with self.subTest(seller=seller):
                move, _attachment = self._make_move(xml_content)
                html = self.env['ir.actions.report']._render_qweb_html(
                    'account_edi_ubl_cii.action_report_invoice_xml_readable', move.ids,
                )[0].decode()
                positions = [html.index(label) for label in SECTION_ORDER]
                self.assertEqual(positions, sorted(positions))
                self.assertLess(html.index('Legal mentions'), html.index(line_name))
                self.assertIn(seller, html)
                self.assertIn('Client SARL', html)
                self.assertIn('Entrepot Client', html)
                self.assertIn('Factor SA', html)
                self.assertNotIn(move.partner_id.name, html)

    def test_import_hook_skips_facturx_originator(self):
        move, _attachment = self._make_move(UBL_INVOICE)
        tree = etree.fromstring(UBL_INVOICE)
        originator = self.env['ir.attachment'].create({
            'name': 'original.pdf',
            'raw': b'%PDF-supplier',
            'mimetype': 'application/pdf',
            'res_model': 'account.move',
            'res_id': move.id,
        })
        move.message_main_attachment_id = originator
        with patch.object(type(self.env['ir.actions.report']), '_run_wkhtmltopdf', return_value=b'%PDF-1.4 readable') as render:
            stored = self.env['account.edi.xml.ubl_bis3']._generate_pdf_attachment(
                move, tree, {'originator_pdf': originator},
            )
            render.assert_not_called()
        self.assertFalse(stored)
        self.assertEqual(move.message_main_attachment_id, originator)
