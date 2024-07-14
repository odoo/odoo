# coding: utf-8
import base64
from pytz import timezone
from datetime import datetime

from odoo.tests import tagged
from odoo.tools import misc
from odoo.modules import module as modules
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon

MAX_WAIT_ITER = 6
CODE_98_ERROR_MSG = "<p>The cancellation request has not yet finished processing by SUNAT. Please retry in a few minutes.<br><br><b>SOAP status code: </b>98</p>"


def mocked_l10n_pe_edi_post_invoice_web_service(edi_format, invoice, edi_filename, edi_str):
    # simulate the EDI always success.
    zip_edi_str = edi_format._l10n_pe_edi_zip_edi_document([('%s.xml' % edi_filename, edi_str)])
    return {
        'attachment': edi_format.env['ir.attachment'].create({
            'res_model': invoice._name,
            'res_id': invoice.id,
            'type': 'binary',
            'name': '%s.zip' % edi_filename,
            'datas': base64.encodebytes(zip_edi_str),
            'mimetype': 'application/zip',
        })
    }


class TestPeEdiCommon(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='pe', edi_format_ref='l10n_pe_edi.edi_pe_ubl_2_1'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.frozen_today = datetime(year=2017, month=1, day=1, hour=0, minute=0, second=0, tzinfo=timezone('utc'))

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        # Replace USD by the fake currency created in setup (GOL).
        cls.env.ref('base.USD').name = "OLD_USD"
        cls.currency_data['currency'].name = 'USD'
        cls.currency_data['currency'].rounding = 0.01

        # ==== Config ====

        cls.certificate = cls.env['l10n_pe_edi.certificate'].create({
            'content': base64.encodebytes(
                misc.file_open('l10n_pe_edi/demo/certificates/certificate.pfx', 'rb').read()),
            'password': '12345678a',
        })
        cls.certificate.write({
            'date_start': '2016-01-01 01:00:00',
            'date_end': '2018-01-01 01:00:00',
        })

        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.pe').id,
            'l10n_pe_edi_provider': 'digiflow',
            'l10n_pe_edi_certificate_id': cls.certificate.id,
            'l10n_pe_edi_test_env': True,
        })

        cls.national_bank = cls.env.ref("l10n_pe.peruvian_national_bank")
        cls.national_bank_account = cls.env['res.partner.bank'].create({
            'acc_number': 'CUENTAPRUEBA',
            'bank_id': cls.national_bank.id,
            'partner_id': cls.company_data['company'].partner_id.id
        })
        cls.company_data['company'].partner_id.write({
            'vat': "20557912879",
            'l10n_latam_identification_type_id': cls.env.ref('l10n_pe.it_RUC').id,
        })

        cls.company_data['default_journal_sale'].l10n_latam_use_documents = True

        cls.iap_account = cls.env['iap.account'].create({
            'service_name': 'l10n_pe_edi',
            'company_ids': [(6, 0, cls.company_data['company'].ids)],
        })

        # Prevent the xsd validation because it could lead to a not-deterministic behavior since the xsd is downloaded
        # by a CRON.
        xsd_attachments = cls.env['ir.attachment']
        for doc_type in ('CreditNote', 'DebitNote', 'Invoice'):
            xsd_attachment = cls.env.ref('l10n_pe_edi.UBL-%s-2.1.xsd' % doc_type, raise_if_not_found=False)
            if xsd_attachment:
                xsd_attachments |= xsd_attachment
        if xsd_attachments:
            xsd_attachments.unlink()

        # ==== Business ====

        cls.tax_group = cls.env['account.tax.group'].create({
            'name': "IGV",
            'l10n_pe_edi_code': "IGV",
        })

        cls.tax_18 = cls.env['account.tax'].create({
            'name': 'tax_18',
            'amount_type': 'percent',
            'amount': 18,
            'l10n_pe_edi_tax_code': '1000',
            'l10n_pe_edi_unece_category': 'S',
            'type_tax_use': 'sale',
            'tax_group_id': cls.tax_group.id,
        })

        cls.product = cls.env['product.product'].create({
            'name': 'product_pe',
            'weight': 2,
            'uom_po_id': cls.env.ref('uom.product_uom_kgm').id,
            'uom_id': cls.env.ref('uom.product_uom_kgm').id,
            'lst_price': 1000.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'unspsc_code_id': cls.env.ref('product_unspsc.unspsc_code_01010101').id,
        })

        cls.partner_a.write({
            'vat': '20462509236',
            'l10n_latam_identification_type_id': cls.env.ref('l10n_pe.it_RUC').id,
            'country_id': cls.env.ref('base.pe').id,
        })

        # Invoice name are tracked by the web-services so this constant tries to get a new unique invoice name at each
        # execution.
        cls.time_name = datetime.now().strftime('%H%M%S')

        # Initialize the cancellation request filename sequence, to avoid collisions between different people running
        # the UTs on the same day
        seq = cls.env.ref('l10n_pe_edi.l10n_pe_edi_summary_sequence')
        if seq.number_next_actual < 50:
            seq.write({'number_next': int(cls.time_name[-3:]) + 60})

        # ==== INVOICE ====

        cls.expected_invoice_xml_values = '''
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
                <DueDate>2017-01-01</DueDate>
                <InvoiceTypeCode
                    listID="0101"
                    listAgencyName="PE:SUNAT"
                    listName="Tipo de Documento"
                    listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01">01</InvoiceTypeCode>
                <Note languageLocaleID="1000">NUEVE MIL CUATROCIENTOS CUARENTA Y 00/100 GOLD</Note>
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
                <PaymentTerms>
                    <ID>FormaPago</ID>
                    <PaymentMeansID>Contado</PaymentMeansID>
                </PaymentTerms>
                <TaxTotal>
                    <TaxAmount currencyID="USD">1440.00</TaxAmount>
                    <TaxSubtotal>
                        <TaxableAmount currencyID="USD">8000.00</TaxableAmount>
                        <TaxAmount currencyID="USD">1440.00</TaxAmount>
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
                    <LineExtensionAmount currencyID="USD">8000.00</LineExtensionAmount>
                    <TaxExclusiveAmount currencyID="USD">8000.00</TaxExclusiveAmount>
                    <TaxInclusiveAmount currencyID="USD">9440.00</TaxInclusiveAmount>
                    <PrepaidAmount currencyID="USD">0.00</PrepaidAmount>
                    <PayableAmount currencyID="USD">9440.00</PayableAmount>
                </LegalMonetaryTotal>
                <InvoiceLine>
                    <ID>___ignore___</ID>
                    <InvoicedQuantity unitCode="KGM">5.0</InvoicedQuantity>
                    <LineExtensionAmount currencyID="USD">8000.00</LineExtensionAmount>
                    <PricingReference>
                        <AlternativeConditionPrice>
                            <PriceAmount currencyID="USD">1888.00</PriceAmount>
                            <PriceTypeCode>01</PriceTypeCode>
                        </AlternativeConditionPrice>
                    </PricingReference>
                    <TaxTotal>
                        <TaxAmount currencyID="USD">1440.00</TaxAmount>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">8000.00</TaxableAmount>
                            <TaxAmount currencyID="USD">1440.00</TaxAmount>
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
                        <PriceAmount currencyID="USD">1600.0</PriceAmount>
                    </Price>
                </InvoiceLine>
            </Invoice>
        '''

        # ==== REFUND ====

        cls.expected_refund_xml_values = '''
            <CreditNote>
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
                <CreditNoteTypeCode>381</CreditNoteTypeCode>
                <DocumentCurrencyCode>USD</DocumentCurrencyCode>
                <DiscrepancyResponse>
                    <ResponseCode>01</ResponseCode>
                    <Description>abc</Description>
                </DiscrepancyResponse>
                <OrderReference>
                    <ID>abc</ID>
                </OrderReference>
                <BillingReference>
                    <InvoiceDocumentReference>
                        <ID>___ignore___</ID>
                        <DocumentTypeCode>01</DocumentTypeCode>
                    </InvoiceDocumentReference>
                </BillingReference>
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
                <TaxTotal>
                    <TaxAmount currencyID="USD">1440.00</TaxAmount>
                    <TaxSubtotal>
                        <TaxableAmount currencyID="USD">8000.00</TaxableAmount>
                        <TaxAmount currencyID="USD">1440.00</TaxAmount>
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
                    <LineExtensionAmount currencyID="USD">8000.00</LineExtensionAmount>
                    <TaxExclusiveAmount currencyID="USD">8000.00</TaxExclusiveAmount>
                    <TaxInclusiveAmount currencyID="USD">9440.00</TaxInclusiveAmount>
                    <PrepaidAmount currencyID="USD">0.00</PrepaidAmount>
                    <PayableAmount currencyID="USD">9440.00</PayableAmount>
                </LegalMonetaryTotal>
                <CreditNoteLine>
                    <ID>___ignore___</ID>
                    <CreditedQuantity unitCode="KGM">5.0</CreditedQuantity>
                    <LineExtensionAmount currencyID="USD">8000.00</LineExtensionAmount>
                    <PricingReference>
                        <AlternativeConditionPrice>
                            <PriceAmount currencyID="USD">1888.00</PriceAmount>
                            <PriceTypeCode>01</PriceTypeCode>
                        </AlternativeConditionPrice>
                    </PricingReference>
                    <TaxTotal>
                        <TaxAmount currencyID="USD">1440.00</TaxAmount>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">8000.00</TaxableAmount>
                            <TaxAmount currencyID="USD">1440.00</TaxAmount>
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
                        <PriceAmount currencyID="USD">1600.0</PriceAmount>
                    </Price>
                </CreditNoteLine>
            </CreditNote>
        '''

        # ==== DEBIT NOTE ====

        cls.expected_debit_note_xml_values = '''
            <DebitNote>
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
                <DocumentCurrencyCode>USD</DocumentCurrencyCode>
                <DiscrepancyResponse>
                    <ResponseCode>01</ResponseCode>
                    <Description>abc</Description>
                </DiscrepancyResponse>
                <OrderReference>
                    <ID>abc</ID>
                </OrderReference>
                <BillingReference>
                    <InvoiceDocumentReference>
                        <ID>___ignore___</ID>
                        <DocumentTypeCode>01</DocumentTypeCode>
                    </InvoiceDocumentReference>
                </BillingReference>
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
                <PaymentTerms>
                    <ID>FormaPago</ID>
                    <PaymentMeansID>Contado</PaymentMeansID>
                </PaymentTerms>
                <TaxTotal>
                    <TaxAmount currencyID="USD">1440.00</TaxAmount>
                    <TaxSubtotal>
                        <TaxableAmount currencyID="USD">8000.00</TaxableAmount>
                        <TaxAmount currencyID="USD">1440.00</TaxAmount>
                        <TaxCategory>
                            <TaxScheme>
                                <ID>1000</ID>
                                <Name>IGV</Name>
                                <TaxTypeCode>VAT</TaxTypeCode>
                            </TaxScheme>
                        </TaxCategory>
                    </TaxSubtotal>
                </TaxTotal>
                <RequestedMonetaryTotal>
                    <LineExtensionAmount currencyID="USD">8000.00</LineExtensionAmount>
                    <TaxExclusiveAmount currencyID="USD">8000.00</TaxExclusiveAmount>
                    <TaxInclusiveAmount currencyID="USD">9440.00</TaxInclusiveAmount>
                    <PrepaidAmount currencyID="USD">0.00</PrepaidAmount>
                    <PayableAmount currencyID="USD">9440.00</PayableAmount>
                </RequestedMonetaryTotal>
                <DebitNoteLine>
                    <ID>___ignore___</ID>
                    <DebitedQuantity unitCode="KGM">5.0</DebitedQuantity>
                    <LineExtensionAmount currencyID="USD">8000.00</LineExtensionAmount>
                    <PricingReference>
                        <AlternativeConditionPrice>
                            <PriceAmount currencyID="USD">1888.00</PriceAmount>
                            <PriceTypeCode>01</PriceTypeCode>
                        </AlternativeConditionPrice>
                    </PricingReference>
                    <TaxTotal>
                        <TaxAmount currencyID="USD">1440.00</TaxAmount>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">8000.00</TaxableAmount>
                            <TaxAmount currencyID="USD">1440.00</TaxAmount>
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
                        <PriceAmount currencyID="USD">1600.0</PriceAmount>
                    </Price>
                </DebitNoteLine>
            </DebitNote>
        '''

    def _create_invoice(self, **kwargs):
        vals = {
            'name': 'F FFI-%s1' % self.time_name,
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': self.currency_data['currency'].id,
            'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 2000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            })],
        }
        vals.update(kwargs)
        # Increment the name to make sure it is unique at each call
        self.time_name = str(int(self.time_name) + 1)
        return self.env['account.move'].create(vals)

    def _create_refund(self, **kwargs):
        invoice = self._create_invoice(name='F FFI-%s2' % self.time_name, **kwargs)
        vals = {
            'name': 'F CNE-%s1' % self.time_name,
            'move_type': 'out_refund',
            'ref': 'abc',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': self.currency_data['currency'].id,
            'reversed_entry_id': invoice.id,
            'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type07').id,
            'l10n_pe_edi_refund_reason': '01',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 2000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            })],
        }
        vals.update(kwargs)
        return self.env['account.move'].create(vals)

    def _create_debit_note(self, **kwargs):
        invoice = self._create_invoice(name='F FFI-%s3' % self.time_name, **kwargs)
        vals = {
            'name': 'F NDI-%s1' % self.time_name,
            'move_type': 'out_invoice',
            'ref': 'abc',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': self.currency_data['currency'].id,
            'debit_origin_id': invoice.id,
            'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type08').id,
            'l10n_pe_edi_charge_reason': '01',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 2000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            })],
        }
        vals.update(kwargs)
        return self.env['account.move'].create(vals)
