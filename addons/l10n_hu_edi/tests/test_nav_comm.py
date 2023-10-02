# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

import datetime
import logging

_logger = logging.getLogger(__name__)

do_test = False
PRODUCTION_CRED = []
TEST_CRED = []
try:
    from .credentials import do_test, PRODUCTION_CRED, TEST_CRED
except ImportError:
    _logger.warning("Missing test NAV credentials. Online testing is not possible.")


if do_test:

    def cred_tpl2dict(credentials):
        return {
            "username": credentials[1],
            "password": credentials[2],
            "sign_key": credentials[3],
            "back_key": credentials[4],
        }

    @tagged("post_install_l10n", "-at_install", "post_install", "odootech")
    class TestNavApiLowLevel(TransactionCase):
        def test_nav_api_taxpayerquery_by_param(self):
            NAV_Conn = self.env["l10n_hu.nav_communication"]
            response = NAV_Conn.do_taxpayer_query("27725414-2-13", *PRODUCTION_CRED)

            _logger.info("TAXPAYER QUERY by PARAM response = %s", str(response))

            self.assertEqual(response["response_tag"], "QueryTaxpayerResponse", "Response data type mismatch")
            self.assertEqual(response["funcCode"], "OK", "Response data success mismatch")
            self.assertEqual(response["ShortName"], "Fruitsys Zrt.", "Response data 'ShortName' mismatch")

            # resp_example = {
            #     "response_tag": "QueryTaxpayerResponse",
            #     "http_code": 200,
            #     "response_raw": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><ns2:QueryTaxpayerResponse xmlns="http://schemas.nav.gov.hu/NTCA/1.0/common" xmlns:ns2="http://schemas.nav.gov.hu/OSA/3.0/api" xmlns:ns3="http://schemas.nav.gov.hu/OSA/3.0/base" xmlns:ns4="http://schemas.nav.gov.hu/OSA/3.0/data"><header><requestId>ODOO22422e7ab0c24ae48017ac9acb</requestId><timestamp>2023-08-04T15:44:54.845Z</timestamp><requestVersion>3.0</requestVersion><headerVersion>1.0</headerVersion></header><result><funcCode>OK</funcCode></result><ns2:software><ns2:softwareId>GOODO--ODOO-NAV-GW</ns2:softwareId><ns2:softwareName>Odoo-NAV Gateway Server</ns2:softwareName><ns2:softwareOperation>ONLINE_SERVICE</ns2:softwareOperation><ns2:softwareMainVersion>1.0</ns2:softwareMainVersion><ns2:softwareDevName>Goodo System Kft.</ns2:softwareDevName><ns2:softwareDevContact>info@odoo.technology</ns2:softwareDevContact><ns2:softwareDevCountryCode>HU</ns2:softwareDevCountryCode><ns2:softwareDevTaxNumber>27470217</ns2:softwareDevTaxNumber></ns2:software><ns2:infoDate>2022-10-01T00:00:00.000Z</ns2:infoDate><ns2:taxpayerValidity>true</ns2:taxpayerValidity><ns2:taxpayerData><ns2:taxpayerName>FRUITSYS ZÁRTKÖRŰEN MŰKÖDŐ RÉSZVÉNYTÁRSASÁG</ns2:taxpayerName><ns2:taxpayerShortName>Fruitsys Zrt.</ns2:taxpayerShortName><ns2:taxNumberDetail><ns3:taxpayerId>27725414</ns3:taxpayerId><ns3:vatCode>2</ns3:vatCode><ns3:countyCode>13</ns3:countyCode></ns2:taxNumberDetail><ns2:incorporation>ORGANIZATION</ns2:incorporation><ns2:taxpayerAddressList><ns2:taxpayerAddressItem><ns2:taxpayerAddressType>HQ</ns2:taxpayerAddressType><ns2:taxpayerAddress><ns3:countryCode>HU</ns3:countryCode><ns3:postalCode>2072</ns3:postalCode><ns3:city>ZSÁMBÉK</ns3:city><ns3:streetName>BARTÓK BÉLA</ns3:streetName><ns3:publicPlaceCategory>UTCA</ns3:publicPlaceCategory><ns3:number>8</ns3:number></ns2:taxpayerAddress></ns2:taxpayerAddressItem><ns2:taxpayerAddressItem><ns2:taxpayerAddressType>SITE</ns2:taxpayerAddressType><ns2:taxpayerAddress><ns3:countryCode>HU</ns3:countryCode><ns3:postalCode>1073</ns3:postalCode><ns3:city>BUDAPEST</ns3:city><ns3:streetName>AKÁCFA</ns3:streetName><ns3:publicPlaceCategory>UTCA</ns3:publicPlaceCategory><ns3:number>54</ns3:number><ns3:floor>FSZT</ns3:floor><ns3:door>Ü-2</ns3:door></ns2:taxpayerAddress></ns2:taxpayerAddressItem></ns2:taxpayerAddressList></ns2:taxpayerData></ns2:QueryTaxpayerResponse>',
            #     "requestId": "ODOO22422e7ab0c24ae48017ac9acb",
            #     "funcCode": "OK",
            #     "infoDate": datetime.datetime(2022, 10, 1, 0, 0),
            #     "Validity": True,
            #     "Name": "FRUITSYS ZÁRTKÖRŰEN MŰKÖDŐ RÉSZVÉNYTÁRSASÁG",
            #     "ShortName": "Fruitsys Zrt.",
            #     "incorporation": "ORGANIZATION",
            #     "taxNumber": "27725414",
            #     "vatCode": "2",
            #     "countyCode": "13",
            #     "AddressList": [
            #         {
            #             "Type": "HQ",
            #             "countryCode": "HU",
            #             "postalCode": "2072",
            #             "city": "ZSÁMBÉK",
            #             "streetName": "BARTÓK BÉLA",
            #             "publicPlaceCategory": "UTCA",
            #             "number": "8",
            #         },
            #         {
            #             "Type": "SITE",
            #             "countryCode": "HU",
            #             "postalCode": "1073",
            #             "city": "BUDAPEST",
            #             "streetName": "AKÁCFA",
            #             "publicPlaceCategory": "UTCA",
            #             "number": "54",
            #             "floor": "FSZT",
            #             "door": "Ü-2",
            #         },
            #     ],
            # }

    @tagged("post_install_l10n", "-at_install", "post_install", "odootech")
    class TestNavApiHighLevelProduction(TransactionCase):
        def setUp(self):
            super().setUp()

            self.env.company.write(
                {
                    "country_id": self.env.ref("base.hu").id,
                    "vat": PRODUCTION_CRED[0],
                }
            )
            self.env["res.partner"].flush_model()
            self.env["res.company"].flush_model()

            NAV_Conn = self.env["l10n_hu.nav_communication"]
            self.cred_obj = NAV_Conn.create(
                {
                    **cred_tpl2dict(PRODUCTION_CRED),
                    "company_id": self.env.company.id,
                }
            )
            self.assertEqual(self.cred_obj.state, "prod", "Credential store problem")
            self.assertTrue(
                self.env.company.l10n_hu_production_cred, "Company l10n_hu_production_cred calculation problem"
            )

        def test_nav_api_taxpayerquery_by_obj(self):
            response = self.cred_obj.do_taxpayer_query("27725414-2-13")

            _logger.info("TAXPAYER QUERY by OBJ response = %s", str(response))

            self.assertEqual(response["response_tag"], "QueryTaxpayerResponse", "Response data type mismatch")
            self.assertEqual(response["funcCode"], "OK", "Response data success mismatch")
            self.assertEqual(response["ShortName"], "Fruitsys Zrt.", "Response data 'ShortName' mismatch")

        def test_nav_api_token(self):
            response = self.cred_obj.do_token_request()

            _logger.info("TOKEN response = %s", str(response))

            self.assertEqual(response["response_tag"], "TokenExchangeResponse", "Response data type mismatch")
            self.assertEqual(response["funcCode"], "OK", "Response data success mismatch")
            self.assertIn("ExchangeToken", response, "Response data missing 'ExchangeToken'")
            self.assertGreater(len(response["ExchangeToken"]), 20, "Response data 'ExchangeToken' length error")

            # resp_example = {
            #     "response_tag": "TokenExchangeResponse",
            #     "http_code": 200,
            #     "response_raw": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><TokenExchangeResponse xmlns="http://schemas.nav.gov.hu/OSA/3.0/api" xmlns:ns2="http://schemas.nav.gov.hu/NTCA/1.0/common" xmlns:ns3="http://schemas.nav.gov.hu/OSA/3.0/base" xmlns:ns4="http://schemas.nav.gov.hu/OSA/3.0/data"><ns2:header><ns2:requestId>ODOOde3f7710f7084a539a8ce0aaef</ns2:requestId><ns2:timestamp>2023-08-04T23:35:18.519Z</ns2:timestamp><ns2:requestVersion>3.0</ns2:requestVersion><ns2:headerVersion>1.0</ns2:headerVersion></ns2:header><ns2:result><ns2:funcCode>OK</ns2:funcCode></ns2:result><software><softwareId>ODOOENTERPRISE-160</softwareId><softwareName>Odoo Enterprise</softwareName><softwareOperation>LOCAL_SOFTWARE</softwareOperation><softwareMainVersion>16.0</softwareMainVersion><softwareDevName>OdooTech Zrt.</softwareDevName><softwareDevContact>info@odootech.hu</softwareDevContact><softwareDevCountryCode>HU</softwareDevCountryCode><softwareDevTaxNumber>27470217</softwareDevTaxNumber></software><encodedExchangeToken>KibOKJHh01LuRZjcFz3fzyOc0thOr5xdBgUK6AFXqc+mBZMbOBbIRLOzBZQ5mWoA57fRAAcNnxH2kU94cB8IxQ==</encodedExchangeToken><tokenValidityFrom>2023-08-04T23:35:18.765Z</tokenValidityFrom><tokenValidityTo>2023-08-04T23:40:18.765Z</tokenValidityTo></TokenExchangeResponse>',
            #     "requestId": "ODOOde3f7710f7084a539a8ce0aaef",
            #     "funcCode": "OK",
            #     "encodedExchangeToken": "KibOKJHh01LuRZjcFz3fzyOc0thOr5xdBgUK6AFXqc+mBZMbOBbIRLOzBZQ5mWoA57fRAAcNnxH2kU94cB8IxQ==",
            #     "tokenValidityFrom": datetime.datetime(2023, 8, 4, 23, 35, 18, 765000),
            #     "tokenValidityTo": datetime.datetime(2023, 8, 4, 23, 40, 18, 765000),
            #     "ExchangeToken": "5dca161f-122c-4f15-b572-6c1e6ebacdf149IYB7QLX38T",
            # }

    @tagged("post_install_l10n", "-at_install", "post_install", "odootech")
    class TestNavApiHighLevelTest(TransactionCase):
        def setUp(self):
            super().setUp()

            self.env.company.write(
                {
                    "country_id": self.env.ref("base.hu").id,
                    "vat": TEST_CRED[0],
                }
            )
            self.env["res.partner"].flush_model()
            self.env["res.company"].flush_model()

            NAV_Conn = self.env["l10n_hu.nav_communication"]
            self.cred_obj = NAV_Conn.create(
                {
                    **cred_tpl2dict(TEST_CRED),
                    "company_id": self.env.company.id,
                }
            )
            self.assertEqual(self.cred_obj.state, "test", "Credential store problem")
            self.assertFalse(
                self.env.company.l10n_hu_production_cred, "Company l10n_hu_production_cred calculation problem"
            )

        def test_nav_api_taxpayerquery_by_obj(self):
            # without production credentials taxpayerquery is not possible
            with self.assertRaises(UserError):
                self.cred_obj.do_taxpayer_query("27725414-2-13")


@tagged("post_install_l10n", "-at_install", "post_install", "odootech")
class TestNavApiXmlParsing(TransactionCase):
    def test_parse_response_xml_TokenExchangeResponse(self):
        xml_text = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<TokenExchangeResponse xmlns="http://schemas.nav.gov.hu/OSA/3.0/api" xmlns:ns2="http://schemas.nav.gov.hu/NTCA/1.0/common" xmlns:ns3="http://schemas.nav.gov.hu/OSA/3.0/base"
    xmlns:ns4="http://schemas.nav.gov.hu/OSA/3.0/data">
    <ns2:header>
        <ns2:requestId>ODOO214d6665a54d4443bbbb08defd</ns2:requestId>
        <ns2:timestamp>2023-09-28T19:00:25.582Z</ns2:timestamp>
        <ns2:requestVersion>3.0</ns2:requestVersion>
        <ns2:headerVersion>1.0</ns2:headerVersion>
    </ns2:header>
    <ns2:result>
        <ns2:funcCode>OK</ns2:funcCode>
    </ns2:result>
    <software>
        <softwareId>ODOOENTERPRISE-160</softwareId>
        <softwareName>Odoo Enterprise</softwareName>
        <softwareOperation>LOCAL_SOFTWARE</softwareOperation>
        <softwareMainVersion>16.0+e</softwareMainVersion>
        <softwareDevName>OdooTech Zrt.</softwareDevName>
        <softwareDevContact>info@odootech.hu</softwareDevContact>
        <softwareDevCountryCode>HU</softwareDevCountryCode>
        <softwareDevTaxNumber>32226375</softwareDevTaxNumber>
    </software>
    <encodedExchangeToken>d+kuTTIAB56CcUzDX6yjU5VCJam6RUGzH20I/S+vO5YZYBx9eTyHCtoZwY19J/eAaRSM3162pU6djWsLFr+yFA==</encodedExchangeToken>
    <tokenValidityFrom>2023-09-28T19:00:25.842Z</tokenValidityFrom>
    <tokenValidityTo>2023-09-28T19:05:25.842Z</tokenValidityTo>
</TokenExchangeResponse>"""
        conn = self.env["l10n_hu.nav_communication"]
        xml_object = conn._evaluate_xml_text(xml_text)
        response_parsed = conn._parse_response_xml_TokenExchangeResponse(xml_object, "a6c541OYMO0POHYS")
        response_needed = {
            "encodedExchangeToken": "d+kuTTIAB56CcUzDX6yjU5VCJam6RUGzH20I/S+vO5YZYBx9eTyHCtoZwY19J/eAaRSM3162pU6djWsLFr+yFA==",
            "tokenValidityFrom": datetime.datetime(2023, 9, 28, 19, 0, 25, 842000),
            "tokenValidityTo": datetime.datetime(2023, 9, 28, 19, 5, 25, 842000),
            "ExchangeToken": "364b4544-ddb5-4b3d-8990-2447dcc1e1a74BP9PKDUINQ4",
        }
        self.assertEqual(response_needed, response_parsed, "Wrong: _parse_response_xml_TokenExchangeResponse")

    def test_parse_response_xml_ManageInvoiceResponse(self):
        xml_text = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ManageInvoiceResponse xmlns="http://schemas.nav.gov.hu/OSA/3.0/api" xmlns:ns2="http://schemas.nav.gov.hu/NTCA/1.0/common" xmlns:ns3="http://schemas.nav.gov.hu/OSA/3.0/base"
    xmlns:ns4="http://schemas.nav.gov.hu/OSA/3.0/data">
    <ns2:header>
        <ns2:requestId>ODOO5804bb4c84124721931f363a03</ns2:requestId>
        <ns2:timestamp>2023-09-28T19:00:25.862Z</ns2:timestamp>
        <ns2:requestVersion>3.0</ns2:requestVersion>
        <ns2:headerVersion>1.0</ns2:headerVersion>
    </ns2:header>
    <ns2:result>
        <ns2:funcCode>OK</ns2:funcCode>
    </ns2:result>
    <software>
        <softwareId>ODOOENTERPRISE-160</softwareId>
        <softwareName>Odoo Enterprise</softwareName>
        <softwareOperation>LOCAL_SOFTWARE</softwareOperation>
        <softwareMainVersion>16.0+e</softwareMainVersion>
        <softwareDevName>OdooTech Zrt.</softwareDevName>
        <softwareDevContact>info@odootech.hu</softwareDevContact>
        <softwareDevCountryCode>HU</softwareDevCountryCode>
        <softwareDevTaxNumber>32226375</softwareDevTaxNumber>
    </software>
    <transactionId>4BP9PKL71AK1JSGN</transactionId>
</ManageInvoiceResponse>"""
        conn = self.env["l10n_hu.nav_communication"]
        xml_object = conn._evaluate_xml_text(xml_text)
        response_parsed = conn._parse_response_xml_ManageInvoiceResponse(xml_object)
        response_needed = {"transactionId": "4BP9PKL71AK1JSGN"}
        self.assertEqual(response_needed, response_parsed, "Wrong: _parse_response_xml_ManageInvoiceResponse")

    def test_parse_response_xml_QueryTransactionStatusResponse_01(self):
        xml_text = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:QueryTransactionStatusResponse xmlns="http://schemas.nav.gov.hu/NTCA/1.0/common" xmlns:ns2="http://schemas.nav.gov.hu/OSA/3.0/api" xmlns:ns3="http://schemas.nav.gov.hu/OSA/3.0/base"
    xmlns:ns4="http://schemas.nav.gov.hu/OSA/3.0/data">
    <header>
        <requestId>ODOO218e3a9fa6294341bbcd00bc65</requestId>
        <timestamp>2023-09-28T19:00:27.670Z</timestamp>
        <requestVersion>3.0</requestVersion>
        <headerVersion>1.0</headerVersion>
    </header>
    <result>
        <funcCode>OK</funcCode>
    </result>
    <ns2:software>
        <ns2:softwareId>ODOOENTERPRISE-160</ns2:softwareId>
        <ns2:softwareName>Odoo Enterprise</ns2:softwareName>
        <ns2:softwareOperation>LOCAL_SOFTWARE</ns2:softwareOperation>
        <ns2:softwareMainVersion>16.0+e</ns2:softwareMainVersion>
        <ns2:softwareDevName>OdooTech Zrt.</ns2:softwareDevName>
        <ns2:softwareDevContact>info@odootech.hu</ns2:softwareDevContact>
        <ns2:softwareDevCountryCode>HU</ns2:softwareDevCountryCode>
        <ns2:softwareDevTaxNumber>32226375</ns2:softwareDevTaxNumber>
    </ns2:software>
    <ns2:processingResults>
        <ns2:processingResult>
            <ns2:index>1</ns2:index>
            <ns2:invoiceStatus>ABORTED</ns2:invoiceStatus>
            <ns2:technicalValidationMessages>
                <validationResultCode>ERROR</validationResultCode>
                <validationErrorCode>SCHEMA_VIOLATION</validationErrorCode>
                <message>XML contains on line: [2] and column: [1,018] error: [cvc-pattern-valid: Value '1234567812345678' is not facet-valid with respect to pattern
                    '[0-9]{8}[-][0-9]{8}[-][0-9]{8}|[0-9]{8}[-][0-9]{8}|[A-Z]{2}[0-9]{2}[0-9A-Za-z]{11,30}' for type 'BankAccountNumberType'.]</message>
            </ns2:technicalValidationMessages>
            <ns2:technicalValidationMessages>
                <validationResultCode>ERROR</validationResultCode>
                <validationErrorCode>SCHEMA_VIOLATION</validationErrorCode>
                <message>XML contains on line: [2] and column: [1,018] error: [cvc-type.3.1.3: The value '1234567812345678' of element 'supplierBankAccountNumber' is not valid.]</message>
            </ns2:technicalValidationMessages>
            <ns2:technicalValidationMessages>
                <validationResultCode>ERROR</validationResultCode>
                <validationErrorCode>SCHEMA_VIOLATION</validationErrorCode>
                <message>XML contains on line: [2] and column: [1,831] error: [cvc-type.3.1.1: Element 'paymentMethod' is a simple type, so it cannot have attributes, excepting those whose namespace name is identical to
                    'http://www.w3.org/2001/XMLSchema-instance' and whose [local name] is one of 'type', 'nil', 'schemaLocation' or 'noNamespaceSchemaLocation'. However, the attribute, 'if' was found.]</message>
            </ns2:technicalValidationMessages>
            <ns2:technicalValidationMessages>
                <validationResultCode>ERROR</validationResultCode>
                <validationErrorCode>SCHEMA_VIOLATION</validationErrorCode>
                <message>Xml validation failed</message>
            </ns2:technicalValidationMessages>
            <ns2:compressedContentIndicator>false</ns2:compressedContentIndicator>
        </ns2:processingResult>
        <ns2:originalRequestVersion>3.0</ns2:originalRequestVersion>
    </ns2:processingResults>
</ns2:QueryTransactionStatusResponse>"""
        conn = self.env["l10n_hu.nav_communication"]
        xml_object = conn._evaluate_xml_text(xml_text)
        response_parsed = conn._parse_response_xml_QueryTransactionStatusResponse(xml_object)
        response_needed = {
            "invoices": {
                1: {
                    "index": 1,
                    "invoiceStatus": "ABORTED",
                    "compressedContentIndicator": False,
                    "technicalValidationMessages": [
                        {
                            "validationResultCode": "ERROR",
                            "validationErrorCode": "SCHEMA_VIOLATION",
                            "message": "XML contains on line: [2] and column: [1,018] error: [cvc-pattern-valid: Value '1234567812345678' is not facet-valid with respect to pattern\n                    '[0-9]{8}[-][0-9]{8}[-][0-9]{8}|[0-9]{8}[-][0-9]{8}|[A-Z]{2}[0-9]{2}[0-9A-Za-z]{11,30}' for type 'BankAccountNumberType'.]",
                        },
                        {
                            "validationResultCode": "ERROR",
                            "validationErrorCode": "SCHEMA_VIOLATION",
                            "message": "XML contains on line: [2] and column: [1,018] error: [cvc-type.3.1.3: The value '1234567812345678' of element 'supplierBankAccountNumber' is not valid.]",
                        },
                        {
                            "validationResultCode": "ERROR",
                            "validationErrorCode": "SCHEMA_VIOLATION",
                            "message": "XML contains on line: [2] and column: [1,831] error: [cvc-type.3.1.1: Element 'paymentMethod' is a simple type, so it cannot have attributes, excepting those whose namespace name is identical to\n                    'http://www.w3.org/2001/XMLSchema-instance' and whose [local name] is one of 'type', 'nil', 'schemaLocation' or 'noNamespaceSchemaLocation'. However, the attribute, 'if' was found.]",
                        },
                        {
                            "validationResultCode": "ERROR",
                            "validationErrorCode": "SCHEMA_VIOLATION",
                            "message": "Xml validation failed",
                        },
                    ],
                    "businessValidationMessages": [],
                }
            },
            "originalRequestVersion": "3.0",
        }
        self.assertEqual(
            response_needed, response_parsed, "Wrong: _parse_response_xml_QueryTransactionStatusResponse test:1"
        )

    def test_parse_response_xml_QueryTransactionStatusResponse_02(self):
        xml_text = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:QueryTransactionStatusResponse xmlns="http://schemas.nav.gov.hu/NTCA/1.0/common" xmlns:ns2="http://schemas.nav.gov.hu/OSA/3.0/api" xmlns:ns3="http://schemas.nav.gov.hu/OSA/3.0/base"
    xmlns:ns4="http://schemas.nav.gov.hu/OSA/3.0/data">
    <header>
        <requestId>ODOO3a15385713c6410b90531e2701</requestId>
        <timestamp>2023-10-02T09:28:25.689Z</timestamp>
        <requestVersion>3.0</requestVersion>
        <headerVersion>1.0</headerVersion>
    </header>
    <result>
        <funcCode>OK</funcCode>
    </result>
    <ns2:software>
        <ns2:softwareId>ODOOENTERPRISE-160</ns2:softwareId>
        <ns2:softwareName>Odoo Enterprise</ns2:softwareName>
        <ns2:softwareOperation>LOCAL_SOFTWARE</ns2:softwareOperation>
        <ns2:softwareMainVersion>16.0+e</ns2:softwareMainVersion>
        <ns2:softwareDevName>OdooTech Zrt.</ns2:softwareDevName>
        <ns2:softwareDevContact>info@odootech.hu</ns2:softwareDevContact>
        <ns2:softwareDevCountryCode>HU</ns2:softwareDevCountryCode>
        <ns2:softwareDevTaxNumber>32226375</ns2:softwareDevTaxNumber>
    </ns2:software>
    <ns2:processingResults>
        <ns2:processingResult>
            <ns2:index>1</ns2:index>
            <ns2:invoiceStatus>DONE</ns2:invoiceStatus>
            <ns2:businessValidationMessages>
                <ns2:validationResultCode>WARN</ns2:validationResultCode>
                <ns2:validationErrorCode>INCORRECT_SUMMARY_DATA_INVOICE_NET_AMOUNT</ns2:validationErrorCode>
                <ns2:message>Eredeti (CREATE) számla nettó összege nem lehet negatív.</ns2:message>
                <ns2:pointer>
                    <ns2:tag>InvoiceData/invoiceMain/invoice/invoiceSummary/summaryNormal/invoiceNetAmount</ns2:tag>
                    <ns2:value>-36.91</ns2:value>
                </ns2:pointer>
            </ns2:businessValidationMessages>
            <ns2:businessValidationMessages>
                <ns2:validationResultCode>WARN</ns2:validationResultCode>
                <ns2:validationErrorCode>INCORRECT_SUMMARY_DATA_VAT_OUT_OF_SCOPE</ns2:validationErrorCode>
                <ns2:message>Az Áfa törvény hatályán kívüli jelölés a tételsorok és az összesítő közül csak az egyikben fordul elő, a másikból hiányzik.</ns2:message>
                <ns2:pointer>
                    <ns2:tag>InvoiceData/invoiceMain/invoice/invoiceSummary/summaryNormal/summaryByVatRate/vatRate/vatOutOfScope/case</ns2:tag>
                    <ns2:value>ATK</ns2:value>
                </ns2:pointer>
            </ns2:businessValidationMessages>
            <ns2:compressedContentIndicator>false</ns2:compressedContentIndicator>
        </ns2:processingResult>
        <ns2:originalRequestVersion>3.0</ns2:originalRequestVersion>
    </ns2:processingResults>
</ns2:QueryTransactionStatusResponse>"""
        conn = self.env["l10n_hu.nav_communication"]
        xml_object = conn._evaluate_xml_text(xml_text)
        response_parsed = conn._parse_response_xml_QueryTransactionStatusResponse(xml_object)
        response_needed = {
            "invoices": {
                1: {
                    "index": 1,
                    "invoiceStatus": "DONE",
                    "compressedContentIndicator": False,
                    "technicalValidationMessages": [],
                    "businessValidationMessages": [
                        {
                            "validationResultCode": "WARN",
                            "validationErrorCode": "INCORRECT_SUMMARY_DATA_INVOICE_NET_AMOUNT",
                            "message": "Eredeti (CREATE) számla nettó összege nem lehet negatív.",
                            "pointer": [
                                {
                                    "tag": "InvoiceData/invoiceMain/invoice/invoiceSummary/summaryNormal/invoiceNetAmount",
                                    "value": "-36.91",
                                }
                            ],
                        },
                        {
                            "validationResultCode": "WARN",
                            "validationErrorCode": "INCORRECT_SUMMARY_DATA_VAT_OUT_OF_SCOPE",
                            "message": "Az Áfa törvény hatályán kívüli jelölés a tételsorok és az összesítő közül csak az egyikben fordul elő, a másikból hiányzik.",
                            "pointer": [
                                {
                                    "tag": "InvoiceData/invoiceMain/invoice/invoiceSummary/summaryNormal/summaryByVatRate/vatRate/vatOutOfScope/case",
                                    "value": "ATK",
                                }
                            ],
                        },
                    ],
                }
            },
            "originalRequestVersion": "3.0",
        }
        self.assertEqual(
            response_needed, response_parsed, "Wrong: _parse_response_xml_QueryTransactionStatusResponse test:2"
        )
