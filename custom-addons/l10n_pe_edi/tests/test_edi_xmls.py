# -*- coding: utf-8 -*
from odoo import Command
from odoo.tests import tagged
from .common import TestPeEdiCommon, mocked_l10n_pe_edi_post_invoice_web_service
from unittest.mock import patch

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiXmls(TestPeEdiCommon):

    def test_price_amount_rounding(self):
        with freeze_time(self.frozen_today), \
            patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_invoice(invoice_line_ids=[(0, 0, {
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 83.6,  # We will compute 250.8 / 3, which results in 83.60000000000001. It must be rounded.
                'quantity': 3,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            })])
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            etree = self.get_xml_tree_from_string(edi_xml)
            price_amount = etree.find('.//{*}InvoiceLine/{*}Price/{*}PriceAmount')
            self.assertEqual(price_amount.text, '83.6')

    def test_invoice_simple_case(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_invoice()
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)
            expected_etree = self.get_xml_tree_from_string(self.expected_invoice_xml_values)
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_refund_simple_case(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_refund()
            (move.reversed_entry_id + move).action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)
            expected_etree = self.get_xml_tree_from_string(self.expected_refund_xml_values)
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_debit_note_simple_case(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_debit_note()
            (move.debit_origin_id + move).action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)
            expected_etree = self.get_xml_tree_from_string(self.expected_debit_note_xml_values)
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_payment_term_detraction_case(self):
        """ Invoice in USD with detractions and multiple payment term lines"""
        self.product.l10n_pe_withhold_percentage = 10
        self.product.l10n_pe_withhold_code = '001'
        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            update_vals_dict = {"l10n_pe_edi_operation_type": "1001",
                                "invoice_payment_term_id": self.env.ref("account.account_payment_term_advance_60days").id}
            invoice = self._create_invoice(**update_vals_dict).with_context(edi_test_mode=True)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)
        expected_etree = self.get_xml_tree_from_string(self.expected_invoice_xml_values)
        expected_etree = self.with_applied_xpath(
            expected_etree,
            '''
                <xpath expr="//InvoiceTypeCode" position="attributes">
                    <attribute name="listID">1001</attribute>
                </xpath>
                <xpath expr="//Note[1]" position="after">
                    <Note languageLocaleID="2006">Leyenda: Operacion sujeta a detraccion</Note>
                </xpath>
                <xpath expr="//DueDate" position="replace">
                    <DueDate>2017-03-02</DueDate>
                </xpath>
                <xpath expr="//PaymentTerms" position="replace"/>
                <xpath expr="//Delivery" position="after">
                    <PaymentMeans>
                        <ID>Detraccion</ID>
                        <PaymentMeansCode>999</PaymentMeansCode>
                        <PayeeFinancialAccount>
                            <ID>CUENTAPRUEBA</ID>
                        </PayeeFinancialAccount>
                    </PaymentMeans>
                    <PaymentTerms>
                        <ID>Detraccion</ID>
                        <PaymentMeansID>001</PaymentMeansID>
                        <PaymentPercent>10.0</PaymentPercent>
                        <Amount currencyID="PEN">472.00</Amount>
                    </PaymentTerms>
                    <PaymentTerms>
                        <ID>FormaPago</ID>
                        <PaymentMeansID>Credito</PaymentMeansID>
                        <Amount currencyID="USD">8496.00</Amount>
                    </PaymentTerms>
                    <PaymentTerms>
                        <ID>FormaPago</ID>
                        <PaymentMeansID>Cuota001</PaymentMeansID>
                        <Amount currencyID="USD">1888.00</Amount>
                        <PaymentDueDate>2017-01-01</PaymentDueDate>
                    </PaymentTerms>
                    <PaymentTerms>
                        <ID>FormaPago</ID>
                        <PaymentMeansID>Cuota002</PaymentMeansID>
                        <Amount currencyID="USD">6608.00</Amount>
                        <PaymentDueDate>2017-03-02</PaymentDueDate>
                    </PaymentTerms>
                </xpath>
            ''')
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_detraction_with_decimal(self):
        """ Invoice in PEN with detraction containing decimal digits"""
        self.product.l10n_pe_withhold_percentage = 10
        self.product.l10n_pe_withhold_code = '019'

        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            vals = {
                'name': 'F FFI-%s1' % self.time_name,
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2017-01-01',
                'date': '2017-01-01',
                'invoice_payment_term_id': self.env.ref("account.account_payment_term_end_following_month").id,
                'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
                'l10n_pe_edi_operation_type': '1001',
                'invoice_line_ids': [Command.create({
                    'product_id': self.product.id,
                    'price_unit': 990.0,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_18.ids)],
                })],
            }
            invoice = self.env['account.move'].create(vals).with_context(edi_test_mode=True)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)
        expected_invoice_xml_values = '''
            <Invoice>
                <UBLExtensions>
                    <UBLExtension>
                        <ExtensionContent>
                            <Signature Id="placeholder"/>
                        </ExtensionContent>
                    </UBLExtension>
                </UBLExtensions>
                <UBLVersionID>2.1</UBLVersionID>
                <CustomizationID>2.0</CustomizationID>
                <ID>___ignore___</ID>
                <IssueDate>2017-01-01</IssueDate>
                <DueDate>2017-02-28</DueDate>
                <InvoiceTypeCode
                    listID="1001"
                    listAgencyName="PE:SUNAT"
                    listName="Tipo de Documento"
                    listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01">01</InvoiceTypeCode>
                <Note languageLocaleID="1000">MIL CIENTO SESENTA Y OCHO Y 20/100 SOLES</Note>
                <Note languageLocaleID="2006">Leyenda: Operacion sujeta a detraccion</Note>
                <DocumentCurrencyCode>PEN</DocumentCurrencyCode>
                <OrderReference>
                    <ID>___ignore___</ID>
                </OrderReference>
                <Signature>
                    <ID>IDSignKG</ID>
                    <SignatoryParty>
                        <PartyIdentification>
                            <ID>20557912879</ID>
                        </PartyIdentification>
                        <PartyName>
                            <Name>COMPANY_1_DATA</Name>
                        </PartyName>
                    </SignatoryParty>
                    <DigitalSignatureAttachment>
                        <ExternalReference>
                            <URI>#SignVX</URI>
                        </ExternalReference>
                    </DigitalSignatureAttachment>
                </Signature>
                <AccountingSupplierParty>
                    <CustomerAssignedAccountID>20557912879</CustomerAssignedAccountID>
                    <Party>
                        <PartyIdentification>
                            <ID schemeID="6">20557912879</ID>
                        </PartyIdentification>
                        <PartyName>
                            <Name>company_1_data</Name>
                        </PartyName>
                        <PostalAddress>
                            <Country>
                                <IdentificationCode>PE</IdentificationCode>
                                <Name>Peru</Name>
                            </Country>
                        </PostalAddress>
                        <PartyTaxScheme>
                            <RegistrationName>company_1_data</RegistrationName>
                            <CompanyID>20557912879</CompanyID>
                            <RegistrationAddress>
                                <Country>
                                    <IdentificationCode>PE</IdentificationCode>
                                    <Name>Peru</Name>
                                </Country>
                            </RegistrationAddress>
                            <TaxScheme>
                                <ID>VAT</ID>
                            </TaxScheme>
                        </PartyTaxScheme>
                        <PartyLegalEntity>
                            <RegistrationName>company_1_data</RegistrationName>
                            <CompanyID>20557912879</CompanyID>
                            <RegistrationAddress>
                                <AddressTypeCode>0000</AddressTypeCode>
                                <Country>
                                    <IdentificationCode>PE</IdentificationCode>
                                    <Name>Peru</Name>
                                </Country>
                            </RegistrationAddress>
                        </PartyLegalEntity>
                        <Contact>
                            <ID>___ignore___</ID>
                            <Name>company_1_data</Name>
                        </Contact>
                    </Party>
                </AccountingSupplierParty>
                <AccountingCustomerParty>
                    <AdditionalAccountID>6</AdditionalAccountID>
                    <Party>
                        <PartyIdentification>
                            <ID schemeID="6">20462509236</ID>
                        </PartyIdentification>
                        <PartyName>
                            <Name>partner_a</Name>
                        </PartyName>
                        <PostalAddress>
                            <Country>
                                <IdentificationCode>PE</IdentificationCode>
                                <Name>Peru</Name>
                            </Country>
                        </PostalAddress>
                        <PartyTaxScheme>
                            <RegistrationName>partner_a</RegistrationName>
                            <CompanyID>20462509236</CompanyID>
                            <RegistrationAddress>
                                <Country>
                                    <IdentificationCode>PE</IdentificationCode>
                                    <Name>Peru</Name>
                                </Country>
                            </RegistrationAddress>
                            <TaxScheme>
                                <ID>VAT</ID>
                            </TaxScheme>
                        </PartyTaxScheme>
                        <PartyLegalEntity>
                            <RegistrationName>partner_a</RegistrationName>
                            <CompanyID>20462509236</CompanyID>
                            <RegistrationAddress>
                                <Country>
                                    <IdentificationCode>PE</IdentificationCode>
                                    <Name>Peru</Name>
                                </Country>
                            </RegistrationAddress>
                        </PartyLegalEntity>
                        <Contact>
                            <ID>___ignore___</ID>
                            <Name>partner_a</Name>
                        </Contact>
                    </Party>
                </AccountingCustomerParty>
                <Delivery>
                    <DeliveryLocation>
                        <Address>
                            <Country>
                                <IdentificationCode>PE</IdentificationCode>
                                <Name>Peru</Name>
                            </Country>
                        </Address>
                    </DeliveryLocation>
                </Delivery>
                <PaymentMeans>
                    <ID>Detraccion</ID>
                    <PaymentMeansCode>999</PaymentMeansCode>
                    <PayeeFinancialAccount>
                        <ID>CUENTAPRUEBA</ID>
                    </PayeeFinancialAccount>
                </PaymentMeans>
                <PaymentTerms>
                    <ID>Detraccion</ID>
                    <PaymentMeansID>019</PaymentMeansID>
                    <PaymentPercent>10.0</PaymentPercent>
                    <Amount currencyID="PEN">117.00</Amount>
                </PaymentTerms>
                <PaymentTerms>
                    <ID>FormaPago</ID>
                    <PaymentMeansID>Credito</PaymentMeansID>
                    <Amount currencyID="PEN">1051.20</Amount>
                </PaymentTerms>
                <PaymentTerms>
                    <ID>FormaPago</ID>
                    <PaymentMeansID>Cuota001</PaymentMeansID>
                    <Amount currencyID="PEN">1051.20</Amount>
                    <PaymentDueDate>2017-02-28</PaymentDueDate>
                </PaymentTerms>
                <TaxTotal>
                    <TaxAmount currencyID="PEN">178.20</TaxAmount>
                    <TaxSubtotal>
                        <TaxableAmount currencyID="PEN">990.00</TaxableAmount>
                        <TaxAmount currencyID="PEN">178.20</TaxAmount>
                        <TaxCategory>
                            <TaxScheme>
                                <ID>1000</ID>
                                <Name>IGV</Name>
                                <TaxTypeCode>VAT</TaxTypeCode>
                            </TaxScheme>
                        </TaxCategory>
                    </TaxSubtotal>
                </TaxTotal>
                <LegalMonetaryTotal>
                    <LineExtensionAmount currencyID="PEN">990.00</LineExtensionAmount>
                    <TaxExclusiveAmount currencyID="PEN">990.00</TaxExclusiveAmount>
                    <TaxInclusiveAmount currencyID="PEN">1168.20</TaxInclusiveAmount>
                    <PrepaidAmount currencyID="PEN">0.00</PrepaidAmount>
                    <PayableAmount currencyID="PEN">1168.20</PayableAmount>
                </LegalMonetaryTotal>
                <InvoiceLine>
                    <ID>1</ID>
                    <InvoicedQuantity unitCode="KGM">1.0</InvoicedQuantity>
                    <LineExtensionAmount currencyID="PEN">990.00</LineExtensionAmount>
                    <PricingReference>
                        <AlternativeConditionPrice>
                            <PriceAmount currencyID="PEN">1168.20</PriceAmount>
                            <PriceTypeCode>01</PriceTypeCode>
                        </AlternativeConditionPrice>
                    </PricingReference>
                    <TaxTotal>
                        <TaxAmount currencyID="PEN">178.20</TaxAmount>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="PEN">990.00</TaxableAmount>
                            <TaxAmount currencyID="PEN">178.20</TaxAmount>
                            <TaxCategory>
                                <Percent>18.0</Percent>
                                <TaxExemptionReasonCode>10</TaxExemptionReasonCode>
                                <TaxScheme>
                                    <ID>1000</ID>
                                    <Name>IGV</Name>
                                    <TaxTypeCode>VAT</TaxTypeCode>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                    </TaxTotal>
                    <Item>
                        <Description>product_pe</Description>
                        <Name>product_pe</Name>
                        <CommodityClassification>
                            <ItemClassificationCode>01010101</ItemClassificationCode>
                        </CommodityClassification>
                        <ClassifiedTaxCategory>
                            <ID>S</ID>
                            <Percent>18.0</Percent>
                            <TaxScheme>
                                <ID>VAT</ID>
                            </TaxScheme>
                        </ClassifiedTaxCategory>
                    </Item>
                    <Price>
                        <PriceAmount currencyID="PEN">990.0</PriceAmount>
                    </Price>
                </InvoiceLine>
            </Invoice>
        '''
        expected_etree = self.get_xml_tree_from_string(expected_invoice_xml_values)
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_detraction_with_decimal_foreign_currency(self):
        """ Invoice in USD with detraction containing decimal digits"""
        self.product.l10n_pe_withhold_percentage = 10
        self.product.l10n_pe_withhold_code = '019'

        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            vals = {
                'name': 'F FFI-%s1' % self.time_name,
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2017-01-01',
                'date': '2017-01-01',
                'currency_id': self.currency_data['currency'].id,
                'invoice_payment_term_id': self.env.ref("account.account_payment_term_end_following_month").id,
                'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
                'l10n_pe_edi_operation_type': '1001',
                'invoice_line_ids': [Command.create({
                    'product_id': self.product.id,
                    'price_unit': 990.0,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_18.ids)],
                })],
            }
            invoice = self.env['account.move'].create(vals).with_context(edi_test_mode=True)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)
        expected_invoice_xml_values = '''
            <Invoice>
                <UBLExtensions>
                    <UBLExtension>
                        <ExtensionContent>
                            <Signature Id="placeholder"/>
                        </ExtensionContent>
                    </UBLExtension>
                </UBLExtensions>
                <UBLVersionID>2.1</UBLVersionID>
                <CustomizationID>2.0</CustomizationID>
                <ID>___ignore___</ID>
                <IssueDate>2017-01-01</IssueDate>
                <DueDate>2017-02-28</DueDate>
                <InvoiceTypeCode
                    listID="1001"
                    listAgencyName="PE:SUNAT"
                    listName="Tipo de Documento"
                    listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01">01</InvoiceTypeCode>
                <Note languageLocaleID="1000">MIL CIENTO SESENTA Y OCHO Y 20/100 GOLD</Note>
                <Note languageLocaleID="2006">Leyenda: Operacion sujeta a detraccion</Note>
                <DocumentCurrencyCode>USD</DocumentCurrencyCode>
                <OrderReference>
                    <ID>___ignore___</ID>
                </OrderReference>
                <Signature>
                    <ID>IDSignKG</ID>
                    <SignatoryParty>
                        <PartyIdentification>
                            <ID>20557912879</ID>
                        </PartyIdentification>
                        <PartyName>
                            <Name>COMPANY_1_DATA</Name>
                        </PartyName>
                    </SignatoryParty>
                    <DigitalSignatureAttachment>
                        <ExternalReference>
                            <URI>#SignVX</URI>
                        </ExternalReference>
                    </DigitalSignatureAttachment>
                </Signature>
                <AccountingSupplierParty>
                    <CustomerAssignedAccountID>20557912879</CustomerAssignedAccountID>
                    <Party>
                        <PartyIdentification>
                            <ID schemeID="6">20557912879</ID>
                        </PartyIdentification>
                        <PartyName>
                            <Name>company_1_data</Name>
                        </PartyName>
                        <PostalAddress>
                            <Country>
                                <IdentificationCode>PE</IdentificationCode>
                                <Name>Peru</Name>
                            </Country>
                        </PostalAddress>
                        <PartyTaxScheme>
                            <RegistrationName>company_1_data</RegistrationName>
                            <CompanyID>20557912879</CompanyID>
                            <RegistrationAddress>
                                <Country>
                                    <IdentificationCode>PE</IdentificationCode>
                                    <Name>Peru</Name>
                                </Country>
                            </RegistrationAddress>
                            <TaxScheme>
                                <ID>VAT</ID>
                            </TaxScheme>
                        </PartyTaxScheme>
                        <PartyLegalEntity>
                            <RegistrationName>company_1_data</RegistrationName>
                            <CompanyID>20557912879</CompanyID>
                            <RegistrationAddress>
                                <AddressTypeCode>0000</AddressTypeCode>
                                <Country>
                                    <IdentificationCode>PE</IdentificationCode>
                                    <Name>Peru</Name>
                                </Country>
                            </RegistrationAddress>
                        </PartyLegalEntity>
                        <Contact>
                            <ID>___ignore___</ID>
                            <Name>company_1_data</Name>
                        </Contact>
                    </Party>
                </AccountingSupplierParty>
                <AccountingCustomerParty>
                    <AdditionalAccountID>6</AdditionalAccountID>
                    <Party>
                        <PartyIdentification>
                            <ID schemeID="6">20462509236</ID>
                        </PartyIdentification>
                        <PartyName>
                            <Name>partner_a</Name>
                        </PartyName>
                        <PostalAddress>
                            <Country>
                                <IdentificationCode>PE</IdentificationCode>
                                <Name>Peru</Name>
                            </Country>
                        </PostalAddress>
                        <PartyTaxScheme>
                            <RegistrationName>partner_a</RegistrationName>
                            <CompanyID>20462509236</CompanyID>
                            <RegistrationAddress>
                                <Country>
                                    <IdentificationCode>PE</IdentificationCode>
                                    <Name>Peru</Name>
                                </Country>
                            </RegistrationAddress>
                            <TaxScheme>
                                <ID>VAT</ID>
                            </TaxScheme>
                        </PartyTaxScheme>
                        <PartyLegalEntity>
                            <RegistrationName>partner_a</RegistrationName>
                            <CompanyID>20462509236</CompanyID>
                            <RegistrationAddress>
                                <Country>
                                    <IdentificationCode>PE</IdentificationCode>
                                    <Name>Peru</Name>
                                </Country>
                            </RegistrationAddress>
                        </PartyLegalEntity>
                        <Contact>
                            <ID>___ignore___</ID>
                            <Name>partner_a</Name>
                        </Contact>
                    </Party>
                </AccountingCustomerParty>
                <Delivery>
                    <DeliveryLocation>
                        <Address>
                            <Country>
                                <IdentificationCode>PE</IdentificationCode>
                                <Name>Peru</Name>
                            </Country>
                        </Address>
                    </DeliveryLocation>
                </Delivery>
                <PaymentMeans>
                    <ID>Detraccion</ID>
                    <PaymentMeansCode>999</PaymentMeansCode>
                    <PayeeFinancialAccount>
                        <ID>CUENTAPRUEBA</ID>
                    </PayeeFinancialAccount>
                </PaymentMeans>
                <PaymentTerms>
                    <ID>Detraccion</ID>
                    <PaymentMeansID>019</PaymentMeansID>
                    <PaymentPercent>10.0</PaymentPercent>
                    <Amount currencyID="PEN">58.00</Amount>
                </PaymentTerms>
                <PaymentTerms>
                    <ID>FormaPago</ID>
                    <PaymentMeansID>Credito</PaymentMeansID>
                    <Amount currencyID="USD">1051.38</Amount>
                </PaymentTerms>
                <PaymentTerms>
                    <ID>FormaPago</ID>
                    <PaymentMeansID>Cuota001</PaymentMeansID>
                    <Amount currencyID="USD">1051.38</Amount>
                    <PaymentDueDate>2017-02-28</PaymentDueDate>
                </PaymentTerms>
                <TaxTotal>
                    <TaxAmount currencyID="USD">178.20</TaxAmount>
                    <TaxSubtotal>
                        <TaxableAmount currencyID="USD">990.00</TaxableAmount>
                        <TaxAmount currencyID="USD">178.20</TaxAmount>
                        <TaxCategory>
                            <TaxScheme>
                                <ID>1000</ID>
                                <Name>IGV</Name>
                                <TaxTypeCode>VAT</TaxTypeCode>
                            </TaxScheme>
                        </TaxCategory>
                    </TaxSubtotal>
                </TaxTotal>
                <LegalMonetaryTotal>
                    <LineExtensionAmount currencyID="USD">990.00</LineExtensionAmount>
                    <TaxExclusiveAmount currencyID="USD">990.00</TaxExclusiveAmount>
                    <TaxInclusiveAmount currencyID="USD">1168.20</TaxInclusiveAmount>
                    <PrepaidAmount currencyID="USD">0.00</PrepaidAmount>
                    <PayableAmount currencyID="USD">1168.20</PayableAmount>
                </LegalMonetaryTotal>
                <InvoiceLine>
                    <ID>1</ID>
                    <InvoicedQuantity unitCode="KGM">1.0</InvoicedQuantity>
                    <LineExtensionAmount currencyID="USD">990.00</LineExtensionAmount>
                    <PricingReference>
                        <AlternativeConditionPrice>
                            <PriceAmount currencyID="USD">1168.20</PriceAmount>
                            <PriceTypeCode>01</PriceTypeCode>
                        </AlternativeConditionPrice>
                    </PricingReference>
                    <TaxTotal>
                        <TaxAmount currencyID="USD">178.20</TaxAmount>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">990.00</TaxableAmount>
                            <TaxAmount currencyID="USD">178.20</TaxAmount>
                            <TaxCategory>
                                <Percent>18.0</Percent>
                                <TaxExemptionReasonCode>10</TaxExemptionReasonCode>
                                <TaxScheme>
                                    <ID>1000</ID>
                                    <Name>IGV</Name>
                                    <TaxTypeCode>VAT</TaxTypeCode>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                    </TaxTotal>
                    <Item>
                        <Description>product_pe</Description>
                        <Name>product_pe</Name>
                        <CommodityClassification>
                            <ItemClassificationCode>01010101</ItemClassificationCode>
                        </CommodityClassification>
                        <ClassifiedTaxCategory>
                            <ID>S</ID>
                            <Percent>18.0</Percent>
                            <TaxScheme>
                                <ID>VAT</ID>
                            </TaxScheme>
                        </ClassifiedTaxCategory>
                    </Item>
                    <Price>
                        <PriceAmount currencyID="USD">990.0</PriceAmount>
                    </Price>
                </InvoiceLine>
            </Invoice>
        '''
        expected_etree = self.get_xml_tree_from_string(expected_invoice_xml_values)
        self.assertXmlTreeEqual(current_etree, expected_etree)
