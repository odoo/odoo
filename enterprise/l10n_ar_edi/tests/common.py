# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging
import re
import time
from contextlib import contextmanager
from unittest import mock

from lxml import etree
from requests import Response

from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open
from odoo.tools.zeep import Transport

_logger = logging.getLogger(__name__)


class ArMockedClient:
    @staticmethod
    def get_type(_param):
        return lambda arg: arg


class TestArEdiCommon(TestArCommon):

    @staticmethod
    def setup_afip_ws(afip_ws="wsfe"):
        def _decorator(function):
            def wrapper(self):
                self.afip_ws = afip_ws
                function(self)
            return wrapper

        return _decorator

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subfolder = ""
        cls.ar_private_key = cls.env['certificate.key'].create({
            'name': 'AR Test Private key 1',
            'content': base64.b64encode(file_open("l10n_ar_edi/tests/private_key.pem", 'rb').read()),
        })

        cls.ar_certificate_1 = cls.env['certificate.certificate'].create({
            'name': 'AR Test certificate 1',
            'content': base64.b64encode(file_open("l10n_ar_edi/tests/test_cert1.crt", 'rb').read()),
            'private_key_id': cls.ar_private_key.id,
        })

        cls.ar_certificate_2 = cls.env['certificate.certificate'].create({
            'name': 'AR Test certificate 2',
            'content': base64.b64encode(file_open("l10n_ar_edi/tests/test_cert2.crt", 'rb').read()),
            'private_key_id': cls.ar_private_key.id,
        })

        cls.ar_certificate_3 = cls.env['certificate.certificate'].create({
            'name': 'AR Test certificate 3',
            'content': base64.b64encode(file_open("l10n_ar_edi/tests/test_cert3.crt", 'rb').read()),
            'private_key_id': cls.ar_private_key.id,
        })

        cls.company_ri.write({
            'l10n_ar_afip_ws_environment': 'testing',
            'l10n_ar_afip_ws_key_id': cls.ar_private_key.id,
        })
        cls.company_mono.write({
            'l10n_ar_afip_ws_environment': 'testing',
            'l10n_ar_afip_ws_key_id': cls.ar_private_key.id,
        })

        if 'external' in cls.test_tags:
            cls.company_ri.l10n_ar_afip_ws_crt_id = cls.ar_certificate_1
            cls._create_afip_connections(cls.company_ri, cls.afip_ws)
        else:
            cls.company_ri.l10n_ar_afip_ws_crt_id = False

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    @classmethod
    def _create_afip_connections(cls, company, afip_ws):
        """ Method used to create afip connections and commit then to re use this connections in all the test.
        If a connection can not be set because another instance is already using the certificate then we assign a
        random certificate and try again to create the connections. """
        # In order to connect AFIP we need to create a token which depend on the configured AFIP certificate.
        # If the certificate is been used by another testing instance will raise an error telling us that the token
        # can not be used and need to wait 10 minuts or change with another certificate.
        # To avoid this and always run the unit tests we randonly change the certificate and try to create the
        # connection until there is not token error.
        _logger.log(25, 'Setting homologation private key to company %s', company.name)
        company = company.with_context(l10n_ar_invoice_skip_commit=True)

        for p in range(5):
            try:
                company._l10n_ar_get_connection(afip_ws)
                return
            except Exception as error:
                if 'El CEE ya posee un TA valido para el acceso al WSN solicitado' in repr(error):
                    _logger.log(25, 'Connection Failed')
                elif 'Missing certificate' in repr(error):
                    _logger.log(25, 'Not certificate configured yet')
                else:
                    raise error

                # Set testing certificate
                old = company.l10n_ar_afip_ws_crt_id.name or 'NOT DEFINED'
                current_cert_num = re.findall(r"OdootTestsCert(.)", old)
                current_cert_num = current_cert_num and int(current_cert_num[0]) or 0
                new_cert_number = 1 if current_cert_num == 3 else current_cert_num + 1

                company.l10n_ar_afip_ws_crt_id = cls.env['certificate.certificate'].search([('name', '=', 'AR Test certificate %d' % new_cert_number)], limit=1)
                _logger.log(25, 'Setting demo certificate from %s to %s in %s company' % (
                    old, company.l10n_ar_afip_ws_crt_id.name, company.name))
            time.sleep(2**p)

    def _prepare_multicurrency_values(self):
        super()._prepare_multicurrency_values()
        # Set Rates for USD currency takint into account the value from AFIP
        USD = self.env.ref('base.USD')
        if 'external' in self.test_tags:
            _date, value = USD.with_context(l10n_ar_invoice_skip_commit=True)._l10n_ar_get_afip_ws_currency_rate(self.journal.l10n_ar_afip_ws)
        else:
            # Mock the currency value for standard tests
            value = 1125.3
        self._set_today_rate(USD, 1.0 / value)

    # -------------------------------------------------------------------------
    # Common test methods
    # -------------------------------------------------------------------------

    def _test_ar_edi_common_external(self):
        # Ensure that the connection is made and all the documents are synchronized
        with self.subTest("Test connection"):
            with self.assertRaisesRegex(UserError, '"Check Available AFIP PoS" is not implemented in testing mode for webservice'):
                self.journal.with_context(l10n_ar_invoice_skip_commit=True).l10n_ar_check_afip_pos_number()

        # Ensure basic invoice creation, validation, & consultation process
        with self.subTest("Test consult invoice"):
            invoice = self._create_invoice_ar()
            self._validate_and_review(invoice, "")

            # Consult the info about the last invoice
            last = invoice.journal_id._l10n_ar_get_afip_last_invoice_number(invoice.l10n_latam_document_type_id)
            document_parts = invoice._l10n_ar_get_document_number_parts(invoice.l10n_latam_document_number, invoice.l10n_latam_document_type_id.code)
            self.assertEqual(last, document_parts['invoice_number'])

            # Consult the info about specific invoice
            with self.assertRaisesRegex(UserError, '(CodAutorizacion|Cae).*%s' % invoice.l10n_ar_afip_auth_code):
                self.env['l10n_ar_afip.ws.consult'].create([{
                    'number': last,
                    'journal_id': invoice.journal_id.id,
                    'document_type_id': invoice.l10n_latam_document_type_id.id,
                }]).button_confirm()

    def _test_connection(self):
        """ Review that the connection is made and all the documents are syncronized"""
        with self.assertRaisesRegex(UserError, '"Check Available AFIP PoS" is not implemented in testing mode for webservice'):
            self.journal.with_context(l10n_ar_invoice_skip_commit=True).l10n_ar_check_afip_pos_number()

    def _test_consult_invoice(self):
        invoice = self._create_invoice_ar()
        self._validate_and_review(invoice, "", skip_assert_json=True)

        # Consult the info about the last invoice
        last = invoice.journal_id._l10n_ar_get_afip_last_invoice_number(invoice.l10n_latam_document_type_id)
        document_parts = invoice._l10n_ar_get_document_number_parts(invoice.l10n_latam_document_number, invoice.l10n_latam_document_type_id.code)
        self.assertEqual(last, document_parts['invoice_number'])

        # Consult the info about specific invoice
        with self.assertRaisesRegex(UserError, '(CodAutorizacion|Cae).*%s' % invoice.l10n_ar_afip_auth_code):
            self.env['l10n_ar_afip.ws.consult'].create({'number': last,
                                                        'journal_id': invoice.journal_id.id,
                                                        'document_type_id': invoice.l10n_latam_document_type_id.id}).button_confirm()
        return invoice

    def _test_ar_edi_flow(self, test_name: str, move_type: str, document_code: str, concept: str, **invoice_args):
        _logger.info("Testing subtest: %s", test_name)
        if document_code == 'b':
            invoice_args.setdefault('partner_id', self.partner_cf)
        if concept == 'product':
            invoice_args.setdefault('invoice_line_ids', [self._prepare_invoice_line(product_id=self.product_iva_21, price_unit=100)])
        elif concept == 'service':
            invoice_args.setdefault('invoice_line_ids', [self._prepare_invoice_line(product_id=self.service_iva_27, price_unit=100)])
        else:  # concept == 'product_service'
            invoice_args.setdefault('invoice_line_ids', [
                self._prepare_invoice_line(product_id=self.product_iva_21, price_unit=100),
                self._prepare_invoice_line(product_id=self.service_iva_27, price_unit=100),
            ])

        invoice = self._create_invoice_ar(**invoice_args)
        document_type = f"invoice_{document_code}"
        expected_document = self.document_type[document_type]
        self.assertEqual(invoice.l10n_latam_document_type_id.display_name, expected_document.display_name, 'The document should be %s' % expected_document.display_name)
        self._validate_and_review(invoice, test_name or f"{document_type}_{concept}", skip_assert_json=move_type != 'invoice')

        if move_type in ('credit_note', 'debit_note'):
            if move_type == 'credit_note':
                note_move = self._reverse_invoice(invoice, reason='Mercadería defectuosa')
            else:
                note_move = self._create_debit_note(invoice, reason='Mercadería defectuosa')
            expected_document = self.document_type[f"{move_type}_{document_code}"]
            self.assertEqual(note_move.l10n_latam_document_type_id.display_name, expected_document.display_name, 'The document should be %s' % expected_document.display_name)
            self._validate_and_review(note_move, test_name)

        return invoice

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def _get_afip_pos_system_real_name(cls):
        mapping = super()._get_afip_pos_system_real_name()
        mapping.update({'WSFE': 'RAW_MAW', 'WSFEX': 'FEEWS', 'WSBFE': 'BFEWS'})
        return mapping

    @contextmanager
    def _handler_afip_internal_error(self):
        try:
            yield
        except Exception as exc:
            error_msg = repr(exc)
            if 'Code 500' in error_msg or 'Code 501' in error_msg or 'Code 502' in error_msg:
                self.skipTest("We receive an internal error from AFIP so skip this test")
            else:
                raise

    def _post(self, invoice):
        with self._handler_afip_internal_error():
            invoice.with_context(l10n_ar_invoice_skip_commit=True).action_post()

    def _l10n_ar_verify_on_afip(self, bill):
        with self._handler_afip_internal_error():
            bill.l10n_ar_verify_on_afip()

    def _validate_and_review(self, invoice, test_name: str, document_number='12345-12345678', skip_assert_json=False):
        """ Validate electronic invoice and review that the invoice has been proper validated """
        self._post(invoice)

        if 'external' in self.test_tags:
            # EDI validations
            expected_result = 'A'
            error_msg = 'This test return a result different from the expected (%s)' % expected_result
            self.assertEqual(invoice.l10n_ar_afip_auth_mode, 'CAE', error_msg)
            detail_info = f"{error_msg}\nResponse\n{invoice.l10n_ar_afip_xml_response}\nMsg\n{invoice.message_ids[:1].body}"
            self.assertEqual(invoice.l10n_ar_afip_result, expected_result, detail_info)

            self.assertTrue(invoice.l10n_ar_afip_auth_code, error_msg)
            self.assertTrue(invoice.l10n_ar_afip_auth_code_due, error_msg)
            self.assertTrue(invoice.l10n_ar_afip_xml_request, error_msg)
            self.assertTrue(invoice.l10n_ar_afip_xml_response, error_msg)
        else:
            mocked_client = ArMockedClient()
            invoice.l10n_latam_document_number = document_number
            if invoice.journal_id.l10n_ar_afip_ws == 'wsfe':
                request_data = invoice.wsfe_get_cae_request(mocked_client)
            elif invoice.journal_id.l10n_ar_afip_ws == 'wsfex':
                request_data = invoice.wsfex_get_cae_request(111, mocked_client)
            elif invoice.journal_id.l10n_ar_afip_ws == 'wsbfe':
                request_data = invoice.wsbfe_get_cae_request(222, mocked_client)
            else:
                self.fail(f"Unexpected l10n_ar_afip_ws value on the invoice journal: {invoice.journal_id.l10n_ar_afip_ws}")

            if test_name and not skip_assert_json:
                self.assert_json(request_data, test_name, self.subfolder)

    def _l10n_ar_xml_tag(self, afip_ws, data):
        """ Easy helper to get XML tag for a given purpose data """
        xml_tags = {
            'wsfe': {'currency': 'MonId', 'rate': 'MonCotiz'},
            'wsfex': {'currency': 'Moneda_Id', 'rate': 'Moneda_ctz'},
            'wsbfe': {'currency': 'Imp_moneda_Id', 'rate': 'Imp_moneda_ctz'}}
        return xml_tags[afip_ws][data]

    def _test_payment_foreign_currency(self):
        """ Payment in Foreign Currency  """
        USD = self.env.ref('base.USD')
        self.assertEqual(USD.rate, 1.0)
        self._prepare_multicurrency_values()
        self.assertNotEqual(USD.rate, 1.0)
        afip_ws = self.journal.l10n_ar_afip_ws

        # No + any rate (does not matter rate): Will work always is the current behavior, is the default value
        invoice = self._create_invoice_ar(currency_id=USD)
        self.assertEqual(invoice.l10n_ar_payment_foreign_currency, "No")
        self._validate_and_review(invoice, f"test_{self.subfolder.split('/')[0]}_foreign_currency_no")
        currency_tag = self._l10n_ar_xml_tag(afip_ws, 'currency')
        if 'external' in self.test_tags:
            self.assertIn(f"<ns0:{currency_tag}>DOL</ns0:{currency_tag}>", invoice.l10n_ar_afip_xml_request)
            self.assertIn("<ns0:CanMisMonExt>N</ns0:CanMisMonExt>", invoice.l10n_ar_afip_xml_request)

        # Yes + Correct last business day rate: Will work
        self.env['ir.config_parameter'].sudo().set_param(
            f"l10n_ar_edi.{self.env.company.id}_foreign_currency_payment", "Yes")
        invoice = self._create_invoice_ar(currency_id=USD)
        invoice.company_id._compute_l10n_ar_payment_foreign_currency()
        invoice._compute_l10n_ar_payment_foreign_currency()
        self.assertEqual(invoice.l10n_ar_payment_foreign_currency, "Yes")
        self._validate_and_review(invoice, f"test_{self.subfolder.split('/')[0]}_foreign_currency_yes", document_number='12345-12345679')

        if 'external' in self.test_tags:
            self.assertIn(f"<ns0:{currency_tag}>DOL</ns0:{currency_tag}>", invoice.l10n_ar_afip_xml_request)
            self.assertIn("<ns0:CanMisMonExt>S</ns0:CanMisMonExt>", invoice.l10n_ar_afip_xml_request)

            # Yes + bad rate: Will fail because is not last business day
            USD.rate_ids.rate = USD.rate_ids.rate * 0.10
            invoice = self._create_invoice_ar(currency_id=USD)
            with self.assertRaisesRegex(UserError,
                                        "The rate to be reported.*differs from that of ARCA Remember that if you pay in foreign currency you must use the same rate of the last business day of ARCA"):
                self._validate_and_review(invoice, "", document_number='12345-12345680')

            # Yes + No rate defined: Will raise error
            USD.rate_ids.rate = 1.0
            invoice = self._create_invoice_ar(currency_id=USD)
            with self.assertRaisesRegex(UserError, "The currency rate to be reported.*is not valid. It must be between"):
                self._validate_and_review(invoice, "", document_number='12345-12345681')


class TestArEdiMockedCommon(TestArEdiCommon):
    @contextmanager
    def patch_client(self, responses):
        """ Patch zeep.Transport in l10n_ar_edi/models/l10n_ar_afipws_connection.py"""

        self.maxDiff = None
        # This method can be called from within a @classmethod, instantiate a TestCase when that happens, so we can use test_case.assert*
        test_case = self if hasattr(self.assertEqual, '__self__') else self()

        responses = iter(responses)

        class MockedTransport(Transport):
            def _load_remote_data(self, url):
                """ Before we make any interactions with the server, we first need to get the
                schema of datatypes so we know what services are available. There are only two
                URLS for Argentina (LoginCms, and services.asmx?WSDL) we are testing so we can go
                view these files directly.
                """
                service = url.rpartition("/")[2].partition("?")[0]
                module = 'l10n_ar_edi'
                with file_open(f'{module}/tests/expected_requests/{service}-schema.xml', 'rb') as fd:
                    expected_tree = fd.read()
                return expected_tree

            def post(self, address, message, headers):
                expected_service, expected_request_filename, response_filename = next(responses)
                if 'service.asmx' in address:
                    _, _, service = headers.get('SOAPAction').rpartition("/")
                    service = service[:-1]
                else:
                    _, _, service = address.rpartition("/")

                test_case.assertEqual(service, expected_service)

                module = 'l10n_ar_edi'
                with file_open(f'{module}/tests/expected_requests/{expected_request_filename}.xml', 'rb') as fd:
                    expected_tree = etree.fromstring(fd.read())

                request_tree = etree.fromstring(message)
                try:
                    test_case.assertXmlTreeEqual(request_tree, expected_tree)
                except AssertionError:
                    _logger.error('Unexpected request XML for service %s', service)
                    raise

                with file_open(f'{module}/tests/mocked_responses/{response_filename}.xml', 'rb') as fd:
                    response_content = fd.read()

                response = mock.Mock(spec=Response)
                response.status_code = 200
                response.content = response_content
                response.headers = {'Content-Type': 'text/xml;charset=utf-8'}
                self.xml_request = etree.tostring(
                    request_tree, pretty_print=True).decode('utf-8')
                self.xml_response = etree.tostring(
                    etree.fromstring(response_content), pretty_print=True).decode('utf-8')
                return response

        with mock.patch('odoo.addons.l10n_ar_edi.models.l10n_ar_afipws_connection.ARTransport', new=MockedTransport):
            yield

        if next(responses, None):
            test_case.fail('Not all expected calls were made!')

    @classmethod
    def _create_afip_connections(cls, company, afip_ws):
        # Override to mock the connection instead of actually making the network requests.
        # No need to call super as it is mainly just running the same code in a loop.
        company = company.with_context(l10n_ar_invoice_skip_commit=True)
        with cls.patch_client(cls, [('LoginCms', 'LoginCms-final', 'LoginCms-final')]):
            company._l10n_ar_get_connection(afip_ws)
