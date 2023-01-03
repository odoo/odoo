# coding: utf-8
from lxml import etree
from datetime import datetime
from pytz import timezone

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.modules.module import get_resource_path


def mocked_l10n_sa_post_zatca_edi(edi_format, invoice):
    pass
@tagged('post_install_l10n', '-at_install', 'post_install')
class TestSaEdiCommon(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_sa.sa_chart_template_standard', edi_format_ref='l10n_sa_edi.edi_sa_zatca'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.frozen_date = datetime(year=2022, month=9, day=5, hour=8, minute=20, second=2, tzinfo=timezone('Etc/GMT-3'))
        # Setup company
        cls.company = cls.company_data['company']
        cls.company.name = 'Main Company'
        cls.company.country_id = cls.env['res.country'].search([('code', '=', 'SA')])
        cls.company.email = "info@company.saexample.com"
        cls.company.phone = '+966 51 234 5678'
        cls.customer_invoice_journal = cls.env['account.journal'].search([('company_id', '=', cls.company.id), ('name', '=', 'Customer Invoices')])
        # customer_invoice_journal.l10n_sa_csr = 'LS0tLS1CRUdJTiBDRVJUSUZJQ0FURSBSRVFVRVNULS0tLS0KTUlJQ056Q0NBZDBDQVFBd2daNHhDekFKQmdOVkJBWVRBbE5CTVJNd0VRWURWUVFMREFvek1USXpNVEl6TkRVMgpNUk13RVFZRFZRUUtEQXBUUVNCRGIyMXdZVzU1TVJNd0VRWURWUVFEREFwVFFTQkRiMjF3WVc1NU1SZ3dGZ1lEClZRUmhEQTh6TVRJek1USXpORFUyTkRVMk56TXhEakFNQmdOVkJBZ01CVTFsWTJOaE1TWXdKQVlEVlFRSERCM1kKcDltRTJZWFlyOW1LMlliWXFTRFlwOW1FMllYWmh0bUkyTEhZcVRCV01CQUdCeXFHU000OUFnRUdCU3VCQkFBSwpBMElBQktZejNkNWRCVytzb2NBdHNVR1liLzZiRFNidU9McUFuUU5UNDFnK0I1Si9qZXVzMzhVTTExWU1uS01XCnVxZmJyZ0YvTWhPbEF4Zk5BV3I1VUhZQmN1aWdnZDR3Z2RzR0NTcUdTSWIzRFFFSkRqR0J6VENCeWpBaEJna3IKQmdFRUFZSTNGQUlFRkF3U1drRlVRMEV0UTI5a1pTMVRhV2R1YVc1bk1JR2tCZ05WSFJFRWdad3dnWm1rZ1pZdwpnWk14SURBZUJnTlZCQVFNRnpFdFQyUnZiM3d5TFRFMWZETXRNVEl6TkRVMk56ZzVNUjh3SFFZS0NaSW1pWlB5CkxHUUJBUXdQTXpFeU16RXlNelExTmpRMU5qY3pNUTB3Q3dZRFZRUU1EQVF4TURBd01TOHdMUVlEVlFRYURDWkIKYkNCQmJXbHlJRTF2YUdGdGJXVmtJRUpwYmlCQlltUjFiQ0JCZW1sNklGTjBjbVZsZERFT01Bd0dBMVVFRHd3RgpUM1JvWlhJd0NnWUlLb1pJemowRUF3SURTQUF3UlFJaEFMNWlnNHJLVXY1NGI0VTA1YnU1U3dGU2FKaGFTeTRuCnRxMFRKYittcDJ6aEFpQjhoUjd2TGlVeUhPOHNkRnNYNTBXdDNOemU2M1g0b3RKL1dsN2JKdmpwcEE9PQotLS0tLUVORCBDRVJUSUZJQ0FURSBSRVFVRVNULS0tLS0K'
        # customer_invoice_journal.l10n_sa_compliance_csid_json = '{"requestID": 1234567890123, "dispositionMessage": "ISSUED", "binarySecurityToken": "TUlJQ1hqQ0NBZ1NnQXdJQkFnSUdBWVZUMlAyak1Bb0dDQ3FHU000OUJBTUNNQlV4RXpBUkJnTlZCQU1NQ21WSmJuWnZhV05wYm1jd0hoY05Nakl4TWpJM01UTTFNREF5V2hjTk1qY3hNakkyTWpFd01EQXdXakNCbmpFTE1Ba0dBMVVFQmhNQ1UwRXhFekFSQmdOVkJBc01Dak14TWpNeE1qTTBOVFl4RXpBUkJnTlZCQW9NQ2xOQklFTnZiWEJoYm5reEV6QVJCZ05WQkFNTUNsTkJJRU52YlhCaGJua3hHREFXQmdOVkJHRU1Eek14TWpNeE1qTTBOVFkwTlRZM016RU9NQXdHQTFVRUNBd0ZUV1ZqWTJFeEpqQWtCZ05WQkFjTUhkaW4yWVRaaGRpdjJZclpodGlwSU5pbjJZVFpoZG1HMllqWXNkaXBNRll3RUFZSEtvWkl6ajBDQVFZRks0RUVBQW9EUWdBRXBqUGQzbDBGYjZ5aHdDMnhRWmh2L3BzTkp1NDR1b0NkQTFQaldENEhrbitONjZ6ZnhRelhWZ3ljb3hhNnA5dXVBWDh5RTZVREY4MEJhdmxRZGdGeTZLT0J1RENCdFRBTUJnTlZIUk1CQWY4RUFqQUFNSUdrQmdOVkhSRUVnWnd3Z1pta2daWXdnWk14SURBZUJnTlZCQVFNRnpFdFQyUnZiM3d5TFRFMWZETXRNVEl6TkRVMk56ZzVNUjh3SFFZS0NaSW1pWlB5TEdRQkFRd1BNekV5TXpFeU16UTFOalExTmpjek1RMHdDd1lEVlFRTURBUXhNREF3TVM4d0xRWURWUVFhRENaQmJDQkJiV2x5SUUxdmFHRnRiV1ZrSUVKcGJpQkJZbVIxYkNCQmVtbDZJRk4wY21WbGRERU9NQXdHQTFVRUR3d0ZUM1JvWlhJd0NnWUlLb1pJemowRUF3SURTQUF3UlFJZ2FxU1pRTFdMdkZXT3RaQ05BMWl4TjJkTVZtSGtmUVJpVHllZVRsWFNNcjhDSVFDc3puY3hjd0NMM3NhT3k2ZDF1T3J2N1RxMTl0Y01lc2IzZHBSbVFJcDVJQT09", "secret": "kss5lQZx6iSBG5OWhDjir+Z4FGQce4DzFokXgWEsZtY=", "errors": null}'
        # cls.company.l10n_sa_serial_number = '123456789'
        # cls.company.l10n_sa_private_key = '-----BEGIN EC PRIVATE KEY----- MHQCAQEEIPSllJSoBtrm1jgfTgb38cDbCxMd3CQajX0I7+KUDbYuoAcGBSuBBAAK oUQDQgAEpjPd3l0Fb6yhwC2xQZhv/psNJu44uoCdA1PjWD4Hkn+N66zfxQzXVgyc oxa6p9uuAX8yE6UDF80BavlQdgFy6A== -----END EC PRIVATE KEY----- '
        cls.company.l10n_sa_edi_building_number = '1234'
        cls.company.l10n_sa_edi_plot_identification = '1234'
        cls.company.l10n_sa_edi_neighborhood = 'Testomania'
        cls.company.l10n_sa_additional_identification_number = '2525252525252'
        cls.company.vat = '311111111111113'
        cls.company.l10n_sa_serial_number = '123456789'
        cls.company.state_id = cls.env['res.country.state'].create({
            'name': 'riyadh',
            'code': 'RYA',
            'country_id': cls.company.country_id.id
        })
        cls.company.street = 'Al Amir Mohammed Bin Abdul Aziz Street'
        cls.company.city = 'المدينة المنورة'
        cls.company.zip = '42317'

        cls.customer_invoice_journal.l10n_sa_regen_csr()
        cls.customer_invoice_journal.l10n_sa_api_get_compliance_CSID(otp='123345')
        cls.customer_invoice_journal.l10n_sa_run_compliance_checks()
        cls.customer_invoice_journal.l10n_sa_api_get_production_CSID('123456')
        # Setup partner
        cls.partner_company = cls.env['res.partner'].search([('name', '=', 'Azure Interior')])
        cls.partner_company.write({
            'l10n_sa_edi_building_number': '12300',
            'l10n_sa_edi_plot_identification': '2323',
            'l10n_sa_edi_neighborhood': 'Neighbor!',
            'l10n_sa_additional_identification_number': '353535353535353',
        })
        cls.partner_us = cls.env['res.partner'].create({
            'name': 'Chichi Lboukla',
            'street': '4557 De Silva St',
            'l10n_sa_edi_building_number': '12300',
            'l10n_sa_edi_plot_identification': '2323',
            'l10n_sa_edi_neighborhood': 'Neighbor!',
            'l10n_sa_additional_identification_number': '353535353535353',
            'city': 'Fremont',
            'zip': '94538',
            'country_id': cls.env['res.country'].search([('code', '=', 'US')]).id,
            'state_id': cls.env['res.country.state'].search([('name', '=', 'California')]).id,
            'parent_id':cls.partner_company.id,
            'email': 'azure.Interior24@example.com',
            'phone': '(870)-931-0505',
        })



        # 15% tax
        cls.tax_15 = cls.env['account.tax'].search([('company_id', '=', cls.company.id), ('name', '=', 'Sales Tax 15%')])

        # Large cabinet product
        cls.product = cls.env['product.product'].search([('default_code', '=', 'E-COM07')])

        cls.standard_invoice_xml = get_resource_path('l10n_sa_edi', 'tests/compliance/standard', 'invoice.xml')

        cls.expected_invoice = '''
        <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2">
            <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
            <cbc:ProfileID>reporting:1.0</cbc:ProfileID>
            <cbc:ID>INV/2022/00014</cbc:ID>
            <cbc:UUID>___ignore___</cbc:UUID>
            <cbc:IssueDate>2022-09-05</cbc:IssueDate>
            <cbc:IssueTime>08:20:02</cbc:IssueTime>
            <cbc:InvoiceTypeCode name="0100100">388</cbc:InvoiceTypeCode>
            <cbc:DocumentCurrencyCode>SAR</cbc:DocumentCurrencyCode>
            <cbc:TaxCurrencyCode>SAR</cbc:TaxCurrencyCode>
            <cbc:BuyerReference>Chichi Lboukla</cbc:BuyerReference>
            <cac:AdditionalDocumentReference>
                <cbc:ID>PIH</cbc:ID>
                <cac:Attachment>
                    <cbc:EmbeddedDocumentBinaryObject mimeCode="text/plain">NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ==</cbc:EmbeddedDocumentBinaryObject>
                </cac:Attachment>
            </cac:AdditionalDocumentReference>
            <cac:AdditionalDocumentReference>
                <cbc:ID>ICV</cbc:ID>
                <cbc:UUID>___ignore___</cbc:UUID>
            </cac:AdditionalDocumentReference>
            <cac:AccountingSupplierParty>
                <cac:Party>
                    <cac:PartyIdentification>
                        <cbc:ID schemeID="CRN">2525252525252</cbc:ID>
                    </cac:PartyIdentification>
                    <cac:PartyName>
                        <cbc:Name>Main Company</cbc:Name>
                    </cac:PartyName>
                    <cac:Language>
                        <cbc:LocaleCode>en_US</cbc:LocaleCode>
                    </cac:Language>
                    <cac:PostalAddress>
                        <cbc:StreetName>Al Amir Mohammed Bin Abdul Aziz Street</cbc:StreetName>
                        <cbc:BuildingNumber>1234</cbc:BuildingNumber>
                        <cbc:PlotIdentification>1234</cbc:PlotIdentification>
                        <cbc:CitySubdivisionName>Testomania</cbc:CitySubdivisionName>
                        <cbc:CityName>&#1575;&#1604;&#1605;&#1583;&#1610;&#1606;&#1577; &#1575;&#1604;&#1605;&#1606;&#1608;&#1585;&#1577;</cbc:CityName>
                        <cbc:PostalZone>42317</cbc:PostalZone>
                        <cbc:CountrySubentity>riyadh</cbc:CountrySubentity>
                        <cbc:CountrySubentityCode>RYA</cbc:CountrySubentityCode>
                        <cac:Country>
                            <cbc:IdentificationCode>SA</cbc:IdentificationCode>
                            <cbc:Name>Saudi Arabia</cbc:Name>
                        </cac:Country>
                    </cac:PostalAddress>
                    <cac:PartyTaxScheme>
                        <cbc:CompanyID>311111111111113</cbc:CompanyID>
                        <cac:TaxScheme>
                            <cbc:ID>VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:PartyTaxScheme>
                    <cac:PartyLegalEntity>
                        <cbc:RegistrationName>Main Company</cbc:RegistrationName>
                    </cac:PartyLegalEntity>
                    <cac:Contact>
                        <cbc:Name>Main Company</cbc:Name>
                        <cbc:Telephone>+966 51 234 5678</cbc:Telephone>
                        <cbc:ElectronicMail>info@company.saexample.com</cbc:ElectronicMail>
                    </cac:Contact>
                </cac:Party>
            </cac:AccountingSupplierParty>
            <cac:AccountingCustomerParty>
                <cac:Party>
                    <cac:PartyIdentification>
                        <cbc:ID schemeID="CRN">353535353535353</cbc:ID>
                    </cac:PartyIdentification>
                    <cac:PartyName>
                        <cbc:Name>Chichi Lboukla</cbc:Name>
                    </cac:PartyName>
                    <cac:Language>
                        <cbc:LocaleCode>en_US</cbc:LocaleCode>
                    </cac:Language>
                    <cac:PostalAddress>
                        <cbc:StreetName>4557 De Silva St</cbc:StreetName>
                        <cbc:BuildingNumber>12300</cbc:BuildingNumber>
                        <cbc:PlotIdentification>2323</cbc:PlotIdentification>
                        <cbc:CitySubdivisionName>Neighbor!</cbc:CitySubdivisionName>
                        <cbc:CityName>Fremont</cbc:CityName>
                        <cbc:PostalZone>94538</cbc:PostalZone>
                        <cbc:CountrySubentity>California</cbc:CountrySubentity>
                        <cbc:CountrySubentityCode>CA</cbc:CountrySubentityCode>
                        <cac:Country>
                            <cbc:IdentificationCode>US</cbc:IdentificationCode>
                            <cbc:Name>United States</cbc:Name>
                        </cac:Country>
                    </cac:PostalAddress>
                    <cac:PartyLegalEntity>
                        <cbc:RegistrationName>Chichi Lboukla</cbc:RegistrationName>
                    </cac:PartyLegalEntity>
                    <cac:Contact>
                        <cbc:Name>Chichi Lboukla</cbc:Name>
                        <cbc:Telephone>(870)-931-0505</cbc:Telephone>
                        <cbc:ElectronicMail>azure.Interior24@example.com</cbc:ElectronicMail>
                    </cac:Contact>
                </cac:Party>
            </cac:AccountingCustomerParty>
            <cac:Delivery>
                <cbc:ActualDeliveryDate>2022-09-05</cbc:ActualDeliveryDate>
            </cac:Delivery>
            <cac:PaymentMeans>
                <cbc:PaymentMeansCode listID="UN/ECE 4461">1</cbc:PaymentMeansCode>
                <cbc:PaymentDueDate>2022-09-22</cbc:PaymentDueDate>
                <cbc:InstructionID>INV/2022/00014</cbc:InstructionID>
            </cac:PaymentMeans>
            <cac:TaxTotal>
                <cbc:TaxAmount currencyID="SAR">48.00</cbc:TaxAmount>
                <cac:TaxSubtotal>
                    <cbc:TaxableAmount currencyID="SAR">320.00</cbc:TaxableAmount>
                    <cbc:TaxAmount currencyID="SAR">48.00</cbc:TaxAmount>
                    <cac:TaxCategory>
                        <cbc:ID schemeID="UN/ECE 5305">S</cbc:ID>
                        <cbc:Percent>15.00</cbc:Percent>
                        <cac:TaxScheme>
                            <cbc:ID schemeID="UN/ECE 5153">VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:TaxCategory>
                </cac:TaxSubtotal>
            </cac:TaxTotal>
            <cac:TaxTotal>
                <cbc:TaxAmount currencyID="SAR">48.00</cbc:TaxAmount>
            </cac:TaxTotal>
            <cac:LegalMonetaryTotal>
                <cbc:LineExtensionAmount currencyID="SAR">320.00</cbc:LineExtensionAmount>
                <cbc:TaxExclusiveAmount currencyID="SAR">320.00</cbc:TaxExclusiveAmount>
                <cbc:TaxInclusiveAmount currencyID="SAR">368.00</cbc:TaxInclusiveAmount>
                <cbc:PrepaidAmount currencyID="SAR">0.00</cbc:PrepaidAmount>
                <cbc:PayableAmount currencyID="SAR">368.00</cbc:PayableAmount>
            </cac:LegalMonetaryTotal>
            <cac:InvoiceLine>
                <cbc:ID>___ignore___</cbc:ID>
                <cbc:InvoicedQuantity>1.0</cbc:InvoicedQuantity>
                <cbc:LineExtensionAmount currencyID="SAR">320.00</cbc:LineExtensionAmount>
                <cac:TaxTotal>
                    <cbc:TaxAmount currencyID="SAR">48.00</cbc:TaxAmount>
                    <cbc:RoundingAmount currencyID="SAR">368.00</cbc:RoundingAmount>
                </cac:TaxTotal>
                <cac:Item>
                    <cbc:Description>[E-COM07] Large Cabinet</cbc:Description>
                    <cbc:Name>Large Cabinet</cbc:Name>
                    <cac:SellersItemIdentification>
                        <cbc:ID>E-COM07</cbc:ID>
                    </cac:SellersItemIdentification>
                    <cac:ClassifiedTaxCategory>
                        <cbc:ID schemeID="UN/ECE 5305">S</cbc:ID>
                        <cbc:Percent>15.0</cbc:Percent>
                        <cac:TaxScheme>
                            <cbc:ID schemeID="UN/ECE 5153">VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:ClassifiedTaxCategory>
                </cac:Item>
                <cac:Price>
                    <cbc:PriceAmount currencyID="SAR">320.00</cbc:PriceAmount>
                </cac:Price>
            </cac:InvoiceLine>
        </Invoice>
        '''

        cls.expected_credit_note = '''
        <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
            xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
            xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2">
            <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
            <cbc:ProfileID>reporting:1.0</cbc:ProfileID>
            <cbc:ID>RINV/2022/00006</cbc:ID>
            <cbc:UUID>6c49b8e0-2ce5-11ed-b6c7-c54ae37ec60b</cbc:UUID>
            <cbc:IssueDate>2022-09-05</cbc:IssueDate>
            <cbc:IssueTime>09:39:15</cbc:IssueTime>
            <cbc:InvoiceTypeCode name="0100100">381</cbc:InvoiceTypeCode>
            <cbc:DocumentCurrencyCode>SAR</cbc:DocumentCurrencyCode>
            <cbc:TaxCurrencyCode>SAR</cbc:TaxCurrencyCode>
            <cbc:BuyerReference>Azure Interior</cbc:BuyerReference>
            <cac:OrderReference>
                <cbc:ID>test</cbc:ID>
            </cac:OrderReference>
            <cac:BillingReference>
                <cac:InvoiceDocumentReference>
                    <cbc:ID>test</cbc:ID>
                </cac:InvoiceDocumentReference>
            </cac:BillingReference>
            <cac:AdditionalDocumentReference>
                <cbc:ID>QR</cbc:ID>
                <cac:Attachment>
                    <cbc:EmbeddedDocumentBinaryObject mimeCode="text/plain">
                        AQpTQSBDb21wYW55Ag8zMTExMTExMTExMTExMTMDGTIwMjItMDktMDVUMDk6Mzk6MTUrMDM6MDAEBjM2OC4wMAUFNDguMDA=</cbc:EmbeddedDocumentBinaryObject>
                </cac:Attachment>
            </cac:AdditionalDocumentReference>
            <cac:AdditionalDocumentReference>
                <cbc:ID>PIH</cbc:ID>
                <cac:Attachment>
                    <cbc:EmbeddedDocumentBinaryObject mimeCode="text/plain">
                        NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ==</cbc:EmbeddedDocumentBinaryObject>
                </cac:Attachment>
            </cac:AdditionalDocumentReference>
            <cac:AdditionalDocumentReference>
                <cbc:ID>ICV</cbc:ID>
                <cbc:UUID>137</cbc:UUID>
            </cac:AdditionalDocumentReference>
            <cac:AccountingSupplierParty>
                <cac:Party>
                    <cac:PartyIdentification>
                        <cbc:ID schemeID="CRN">2525252525252</cbc:ID>
                    </cac:PartyIdentification>
                    <cac:PartyName>
                        <cbc:Name>SA Company</cbc:Name>
                    </cac:PartyName>
                    <cac:Language>
                        <cbc:LocaleCode>en_US</cbc:LocaleCode>
                    </cac:Language>
                    <cac:PostalAddress>
                        <cbc:StreetName>Al Amir Mohammed Bin Abdul Aziz Street</cbc:StreetName>
                        <cbc:BuildingNumber>1234</cbc:BuildingNumber>
                        <cbc:PlotIdentification>1234</cbc:PlotIdentification>
                        <cbc:CitySubdivisionName>Testomania</cbc:CitySubdivisionName>
                        <cbc:CityName>&#1575;&#1604;&#1605;&#1583;&#1610;&#1606;&#1577;
                            &#1575;&#1604;&#1605;&#1606;&#1608;&#1585;&#1577;</cbc:CityName>
                        <cbc:PostalZone>42317</cbc:PostalZone>
                        <cbc:CountrySubentity>riyadh</cbc:CountrySubentity>
                        <cbc:CountrySubentityCode>RYA</cbc:CountrySubentityCode>
                        <cac:Country>
                            <cbc:IdentificationCode>SA</cbc:IdentificationCode>
                            <cbc:Name>Saudi Arabia</cbc:Name>
                        </cac:Country>
                    </cac:PostalAddress>
                    <cac:PartyTaxScheme>
                        <cbc:CompanyID>311111111111113</cbc:CompanyID>
                        <cac:TaxScheme>
                            <cbc:ID>VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:PartyTaxScheme>
                    <cac:PartyLegalEntity>
                        <cbc:RegistrationName>SA Company</cbc:RegistrationName>
                    </cac:PartyLegalEntity>
                    <cac:Contact>
                        <cbc:Name>SA Company</cbc:Name>
                        <cbc:Telephone>+966 51 234 5678</cbc:Telephone>
                        <cbc:ElectronicMail>info@company.saexample.com</cbc:ElectronicMail>
                    </cac:Contact>
                </cac:Party>
            </cac:AccountingSupplierParty>
            <cac:AccountingCustomerParty>
                <cac:Party>
                    <cac:PartyIdentification>
                        <cbc:ID schemeID="CRN">353535353535353</cbc:ID>
                    </cac:PartyIdentification>
                    <cac:PartyName>
                        <cbc:Name>Oualid Daikhi</cbc:Name>
                    </cac:PartyName>
                    <cac:Language>
                        <cbc:LocaleCode>en_US</cbc:LocaleCode>
                    </cac:Language>
                    <cac:PostalAddress>
                        <cbc:StreetName>4557 De Silva St</cbc:StreetName>
                        <cbc:BuildingNumber>12300</cbc:BuildingNumber>
                        <cbc:PlotIdentification>2323</cbc:PlotIdentification>
                        <cbc:CitySubdivisionName>Neighbor!</cbc:CitySubdivisionName>
                        <cbc:CityName>Fremont</cbc:CityName>
                        <cbc:PostalZone>94538</cbc:PostalZone>
                        <cbc:CountrySubentity>California</cbc:CountrySubentity>
                        <cbc:CountrySubentityCode>CA</cbc:CountrySubentityCode>
                        <cac:Country>
                            <cbc:IdentificationCode>US</cbc:IdentificationCode>
                            <cbc:Name>United States</cbc:Name>
                        </cac:Country>
                    </cac:PostalAddress>
                    <cac:PartyLegalEntity>
                        <cbc:RegistrationName>Oualid Daikhi</cbc:RegistrationName>
                    </cac:PartyLegalEntity>
                    <cac:Contact>
                        <cbc:Name>Oualid Daikhi</cbc:Name>
                        <cbc:Telephone>(870)-931-0505</cbc:Telephone>
                        <cbc:ElectronicMail>azure.Interior24@example.com</cbc:ElectronicMail>
                    </cac:Contact>
                </cac:Party>
            </cac:AccountingCustomerParty>
            <cac:Delivery>
                <cbc:ActualDeliveryDate>2022-09-05</cbc:ActualDeliveryDate>
            </cac:Delivery>
            <cac:PaymentMeans>
                <cbc:PaymentMeansCode listID="UN/ECE 4461">1</cbc:PaymentMeansCode>
                <cbc:PaymentDueDate>2022-09-05</cbc:PaymentDueDate>
                <cbc:InstructionNote>Ttest</cbc:InstructionNote>
            </cac:PaymentMeans>
            <cac:TaxTotal>
                <cbc:TaxAmount currencyID="SAR">48.00</cbc:TaxAmount>
                <cac:TaxSubtotal>
                    <cbc:TaxableAmount currencyID="SAR">320.00</cbc:TaxableAmount>
                    <cbc:TaxAmount currencyID="SAR">48.00</cbc:TaxAmount>
                    <cac:TaxCategory>
                        <cbc:ID schemeID="UN/ECE 5305">S</cbc:ID>
                        <cbc:Percent>15.00</cbc:Percent>
                        <cac:TaxScheme>
                            <cbc:ID schemeID="UN/ECE 5153">VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:TaxCategory>
                </cac:TaxSubtotal>
            </cac:TaxTotal>
            <cac:TaxTotal>
                <cbc:TaxAmount currencyID="SAR">48.00</cbc:TaxAmount>
            </cac:TaxTotal>
            <cac:LegalMonetaryTotal>
                <cbc:LineExtensionAmount currencyID="SAR">320.00</cbc:LineExtensionAmount>
                <cbc:TaxExclusiveAmount currencyID="SAR">320.00</cbc:TaxExclusiveAmount>
                <cbc:TaxInclusiveAmount currencyID="SAR">368.00</cbc:TaxInclusiveAmount>
                <cbc:PrepaidAmount currencyID="SAR">0.00</cbc:PrepaidAmount>
                <cbc:PayableAmount currencyID="SAR">368.00</cbc:PayableAmount>
            </cac:LegalMonetaryTotal>
            <cac:InvoiceLine>
                <cbc:ID>390</cbc:ID>
                <cbc:InvoicedQuantity>1.0</cbc:InvoicedQuantity>
                <cbc:LineExtensionAmount currencyID="SAR">320.00</cbc:LineExtensionAmount>
                <cac:TaxTotal>
                    <cbc:TaxAmount currencyID="SAR">48.00</cbc:TaxAmount>
                    <cbc:RoundingAmount currencyID="SAR">368.00</cbc:RoundingAmount>
                </cac:TaxTotal>
                <cac:Item>
                    <cbc:Description>[E-COM07] Large Cabinet</cbc:Description>
                    <cbc:Name>Large Cabinet</cbc:Name>
                    <cac:SellersItemIdentification>
                        <cbc:ID>E-COM07</cbc:ID>
                    </cac:SellersItemIdentification>
                    <cac:ClassifiedTaxCategory>
                        <cbc:ID schemeID="UN/ECE 5305">S</cbc:ID>
                        <cbc:Percent>15.0</cbc:Percent>
                        <cac:TaxScheme>
                            <cbc:ID schemeID="UN/ECE 5153">VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:ClassifiedTaxCategory>
                </cac:Item>
                <cac:Price>
                    <cbc:PriceAmount currencyID="SAR">320.00</cbc:PriceAmount>
                </cac:Price>
            </cac:InvoiceLine>
        </Invoice>
        '''

        cls.expected_debit_note = '''
        <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
            xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
            xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2">
            <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
            <cbc:ProfileID>reporting:1.0</cbc:ProfileID>
            <cbc:ID>INV/2022/00015</cbc:ID>
            <cbc:UUID>___ignore___</cbc:UUID>
            <cbc:IssueDate>2022-09-05</cbc:IssueDate>
            <cbc:IssueTime>___ignore___</cbc:IssueTime>
            <cbc:InvoiceTypeCode name="0100100">383</cbc:InvoiceTypeCode>
            <cbc:DocumentCurrencyCode>SAR</cbc:DocumentCurrencyCode>
            <cbc:TaxCurrencyCode>SAR</cbc:TaxCurrencyCode>
            <cbc:BuyerReference>Azure Interior</cbc:BuyerReference>
            <cac:OrderReference>
                <cbc:ID>INV/2022/00014, Totes forgot</cbc:ID>
            </cac:OrderReference>
            <cac:BillingReference>
                <cac:InvoiceDocumentReference>
                    <cbc:ID>INV/2022/00014</cbc:ID>
                </cac:InvoiceDocumentReference>
            </cac:BillingReference>
            <cac:AdditionalDocumentReference>
                <cbc:ID>QR</cbc:ID>
                <cac:Attachment>
                    <cbc:EmbeddedDocumentBinaryObject mimeCode="text/plain">
                        AQpTQSBDb21wYW55Ag8zMTExMTExMTExMTExMTMDGTIwMjItMDktMDVUMDk6NDU6MjcrMDM6MDAEBTE4LjE3BQQyLjM3</cbc:EmbeddedDocumentBinaryObject>
                </cac:Attachment>
            </cac:AdditionalDocumentReference>
            <cac:AdditionalDocumentReference>
                <cbc:ID>PIH</cbc:ID>
                <cac:Attachment>
                    <cbc:EmbeddedDocumentBinaryObject mimeCode="text/plain">
                        NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ==</cbc:EmbeddedDocumentBinaryObject>
                </cac:Attachment>
            </cac:AdditionalDocumentReference>
            <cac:AdditionalDocumentReference>
                <cbc:ID>ICV</cbc:ID>
                <cbc:UUID>138</cbc:UUID>
            </cac:AdditionalDocumentReference>
            <cac:AccountingSupplierParty>
                <cac:Party>
                    <cac:PartyIdentification>
                        <cbc:ID schemeID="CRN">2525252525252</cbc:ID>
                    </cac:PartyIdentification>
                    <cac:PartyName>
                        <cbc:Name>SA Company</cbc:Name>
                    </cac:PartyName>
                    <cac:Language>
                        <cbc:LocaleCode>en_US</cbc:LocaleCode>
                    </cac:Language>
                    <cac:PostalAddress>
                        <cbc:StreetName>Al Amir Mohammed Bin Abdul Aziz Street</cbc:StreetName>
                        <cbc:BuildingNumber>1234</cbc:BuildingNumber>
                        <cbc:PlotIdentification>1234</cbc:PlotIdentification>
                        <cbc:CitySubdivisionName>Testomania</cbc:CitySubdivisionName>
                        <cbc:CityName>&#1575;&#1604;&#1605;&#1583;&#1610;&#1606;&#1577;
                            &#1575;&#1604;&#1605;&#1606;&#1608;&#1585;&#1577;</cbc:CityName>
                        <cbc:PostalZone>42317</cbc:PostalZone>
                        <cbc:CountrySubentity>riyadh</cbc:CountrySubentity>
                        <cbc:CountrySubentityCode>RYA</cbc:CountrySubentityCode>
                        <cac:Country>
                            <cbc:IdentificationCode>SA</cbc:IdentificationCode>
                            <cbc:Name>Saudi Arabia</cbc:Name>
                        </cac:Country>
                    </cac:PostalAddress>
                    <cac:PartyTaxScheme>
                        <cbc:CompanyID>311111111111113</cbc:CompanyID>
                        <cac:TaxScheme>
                            <cbc:ID>VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:PartyTaxScheme>
                    <cac:PartyLegalEntity>
                        <cbc:RegistrationName>SA Company</cbc:RegistrationName>
                    </cac:PartyLegalEntity>
                    <cac:Contact>
                        <cbc:Name>SA Company</cbc:Name>
                        <cbc:Telephone>+966 51 234 5678</cbc:Telephone>
                        <cbc:ElectronicMail>info@company.saexample.com</cbc:ElectronicMail>
                    </cac:Contact>
                </cac:Party>
            </cac:AccountingSupplierParty>
            <cac:AccountingCustomerParty>
                <cac:Party>
                    <cac:PartyIdentification>
                        <cbc:ID schemeID="CRN">353535353535353</cbc:ID>
                    </cac:PartyIdentification>
                    <cac:PartyName>
                        <cbc:Name>El Amri</cbc:Name>
                    </cac:PartyName>
                    <cac:Language>
                        <cbc:LocaleCode>en_US</cbc:LocaleCode>
                    </cac:Language>
                    <cac:PostalAddress>
                        <cbc:StreetName>4557 De Silva St</cbc:StreetName>
                        <cbc:BuildingNumber>12300</cbc:BuildingNumber>
                        <cbc:PlotIdentification>2323</cbc:PlotIdentification>
                        <cbc:CitySubdivisionName>Neighbor!</cbc:CitySubdivisionName>
                        <cbc:CityName>Fremont</cbc:CityName>
                        <cbc:PostalZone>94538</cbc:PostalZone>
                        <cbc:CountrySubentity>California</cbc:CountrySubentity>
                        <cbc:CountrySubentityCode>CA</cbc:CountrySubentityCode>
                        <cac:Country>
                            <cbc:IdentificationCode>US</cbc:IdentificationCode>
                            <cbc:Name>United States</cbc:Name>
                        </cac:Country>
                    </cac:PostalAddress>
                    <cac:PartyLegalEntity>
                        <cbc:RegistrationName>El Amri</cbc:RegistrationName>
                    </cac:PartyLegalEntity>
                    <cac:Contact>
                        <cbc:Name>El Amri</cbc:Name>
                        <cbc:Telephone>(870)-931-0505</cbc:Telephone>
                        <cbc:ElectronicMail>azure.Interior24@example.com</cbc:ElectronicMail>
                    </cac:Contact>
                </cac:Party>
            </cac:AccountingCustomerParty>
            <cac:Delivery>
                <cbc:ActualDeliveryDate>2022-09-05</cbc:ActualDeliveryDate>
            </cac:Delivery>
            <cac:PaymentMeans>
                <cbc:PaymentMeansCode listID="UN/ECE 4461">1</cbc:PaymentMeansCode>
                <cbc:PaymentDueDate>2022-09-05</cbc:PaymentDueDate>
                <cbc:InstructionID>INV/2022/00015</cbc:InstructionID>
                <cbc:InstructionNote>Totes forgot</cbc:InstructionNote>
            </cac:PaymentMeans>
            <cac:TaxTotal>
                <cbc:TaxAmount currencyID="SAR">2.37</cbc:TaxAmount>
                <cac:TaxSubtotal>
                    <cbc:TaxableAmount currencyID="SAR">15.80</cbc:TaxableAmount>
                    <cbc:TaxAmount currencyID="SAR">2.37</cbc:TaxAmount>
                    <cac:TaxCategory>
                        <cbc:ID schemeID="UN/ECE 5305">S</cbc:ID>
                        <cbc:Percent>15.00</cbc:Percent>
                        <cac:TaxScheme>
                            <cbc:ID schemeID="UN/ECE 5153">VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:TaxCategory>
                </cac:TaxSubtotal>
            </cac:TaxTotal>
            <cac:TaxTotal>
                <cbc:TaxAmount currencyID="SAR">2.37</cbc:TaxAmount>
            </cac:TaxTotal>
            <cac:LegalMonetaryTotal>
                <cbc:LineExtensionAmount currencyID="SAR">15.80</cbc:LineExtensionAmount>
                <cbc:TaxExclusiveAmount currencyID="SAR">15.80</cbc:TaxExclusiveAmount>
                <cbc:TaxInclusiveAmount currencyID="SAR">18.17</cbc:TaxInclusiveAmount>
                <cbc:PrepaidAmount currencyID="SAR">0.00</cbc:PrepaidAmount>
                <cbc:PayableAmount currencyID="SAR">18.17</cbc:PayableAmount>
            </cac:LegalMonetaryTotal>
            <cac:InvoiceLine>
                <cbc:ID>393</cbc:ID>
                <cbc:InvoicedQuantity>1.0</cbc:InvoicedQuantity>
                <cbc:LineExtensionAmount currencyID="SAR">15.80</cbc:LineExtensionAmount>
                <cac:TaxTotal>
                    <cbc:TaxAmount currencyID="SAR">2.37</cbc:TaxAmount>
                    <cbc:RoundingAmount currencyID="SAR">18.17</cbc:RoundingAmount>
                </cac:TaxTotal>
                <cac:Item>
                    <cbc:Description>[E-COM08] Storage Box</cbc:Description>
                    <cbc:Name>Storage Box</cbc:Name>
                    <cac:SellersItemIdentification>
                        <cbc:ID>E-COM08</cbc:ID>
                    </cac:SellersItemIdentification>
                    <cac:ClassifiedTaxCategory>
                        <cbc:ID schemeID="UN/ECE 5305">S</cbc:ID>
                        <cbc:Percent>15.0</cbc:Percent>
                        <cac:TaxScheme>
                            <cbc:ID schemeID="UN/ECE 5153">VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:ClassifiedTaxCategory>
                </cac:Item>
                <cac:Price>
                    <cbc:PriceAmount currencyID="SAR">15.80</cbc:PriceAmount>
                </cac:Price>
            </cac:InvoiceLine>
        </Invoice>
        '''

    def _create_invoice(self, **kwargs):
        vals = {
            'name': 'INV/2022/00014',
            'move_type':'out_invoice',
            'company_id': self.company,
            'partner_id': self.partner_us,
            'invoice_date_due': '2022-09-22',
            'currency_id': self.company.currency_id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'price_unit': 320.0,
                'tax_ids':[Command.set(self.tax_15.ids)],
                }),
            ],
        }
        vals.update(kwargs)

        return self.env['account.move'].create(vals)

    def _create_debit_note(self, **kwargs):
        vals = {
            'name': 'INV/2022/00015',
            'move_type':'out_invoice',
            'company_id': self.company,
            'partner_id': self.partner_us,
            'invoice_date_due': '2022-09-22',
            'currency_id': self.company.currency_id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'price_unit': 320.0,
                'tax_ids':[Command.set(self.tax_15.ids)],
                }),
            ],
        }
        vals.update(kwargs)

        return self.env['account.move'].create(vals)

    def _create_credit_note(self, **kwargs):
        vals = {
            'name': 'INV/2022/00006',
            'move_type':'out_refund',
            'company_id': self.company,
            'partner_id': self.partner_us,
            'invoice_date_due': '2022-09-22',
            'currency_id': self.company.currency_id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'price_unit': 320.0,
                'tax_ids':[Command.set(self.tax_15.ids)],
                }),
            ],
        }
        vals.update(kwargs)

        return self.env['account.move'].create(vals)
