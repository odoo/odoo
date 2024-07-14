# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.addons.l10n_ar.tests.common import TestAr
from odoo.tools.misc import file_open
from odoo.tests import tagged
from contextlib import contextmanager
import base64
import logging
import re

_logger = logging.getLogger(__name__)

@tagged('external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestEdi(TestAr):

    @classmethod
    def setUpClass(cls, afip_ws, chart_template_ref='ar_ri'):
        super(TestEdi, cls).setUpClass(chart_template_ref=chart_template_ref)
        cls.company_ri.write({
            'l10n_ar_afip_ws_environment': 'testing',
        })
        cls.company_mono.write({
            'l10n_ar_afip_ws_environment': 'testing',
        })
        cls._create_afip_connections(cls, cls.company_ri, afip_ws, 'test_cert1.crt')

    # Initialition

    def _create_afip_connections(self, company, afip_ws, cert_file):
        """ Method used to create afip connections and commit then to re use this connections in all the test.
        If a connection can not be set because another instance is already using the certificate then we assign a
        random certificate and try again to create the connections. """
        # In order to connect AFIP we need to create a token which depend on the configured AFIP certificate.
        # If the certificate is been used by another testing instance will raise an error telling us that the token
        # can not be used and need to wait 10 minuts or change with another certificate.
        # To avoid this and always run the unit tests we randonly change the certificate and try to create the
        # connection until there is not token error.
        company.l10n_ar_afip_ws_crt = base64.b64encode(file_open("l10n_ar_edi/tests/" + cert_file, 'rb').read())
        company.l10n_ar_afip_ws_key = base64.b64encode(file_open("l10n_ar_edi/tests/private_key.pem", 'rb').read())
        _logger.log(25, 'Setting homologation private key to company %s', company.name)
        company = company.with_context(l10n_ar_invoice_skip_commit=True)
        checked_certificate_token = False

        while not checked_certificate_token:
            try:
                company._l10n_ar_get_connection(afip_ws)
                checked_certificate_token = True
            except Exception as error:
                if 'El CEE ya posee un TA valido para el acceso al WSN solicitado' in repr(error):
                    _logger.log(25, 'Connection Failed')
                elif 'Missing certificate' in repr(error):
                    _logger.log(25, 'Not certificate configured yet')
                else:
                    raise error

                # Set testing certificate
                old = company.l10n_ar_afip_ws_crt_fname or 'NOT DEFINED'
                current_cert_num = re.findall(r"OdootTestsCert(.)", old)
                current_cert_num = current_cert_num and int(current_cert_num[0]) or 0
                new_cert_number = 1 if current_cert_num == 3 else current_cert_num + 1

                company.l10n_ar_afip_ws_crt = base64.b64encode(file_open("l10n_ar_edi/tests/test_cert%d.crt" % new_cert_number, 'rb').read())
                _logger.log(25, 'Setting demo certificate from %s to %s in %s company' % (
                    old, company.l10n_ar_afip_ws_crt_fname, company.name))

    def _prepare_multicurrency_values(self):
        super()._prepare_multicurrency_values()
        # Set Rates for USD currency takint into account the value from AFIP
        USD = self.env.ref('base.USD')
        _date, value = USD.with_context(l10n_ar_invoice_skip_commit=True)._l10n_ar_get_afip_ws_currency_rate()
        self._set_today_rate(USD, 1.0 / value)

    # Re used unit tests methods

    def _test_connection(self):
        """ Review that the connection is made and all the documents are syncronized"""
        with self.assertRaisesRegex(UserError, '"Check Available AFIP PoS" is not implemented in testing mode for webservice'):
            self.journal.with_context(l10n_ar_invoice_skip_commit=True).l10n_ar_check_afip_pos_number()

    def _test_consult_invoice(self, expected_result=None):
        invoice = self._create_invoice_product()
        self._validate_and_review(invoice, expected_result=expected_result)

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

    def _test_case(self, document_type, concept, forced_values=None, expected_document=None, expected_result=None):
        values = {}
        forced_values = forced_values or {}
        create_invoice = {'product': self._create_invoice_product,
                          'service': self._create_invoice_service,
                          'product_service': self._create_invoice_product_service}
        create_invoice = create_invoice.get(concept)
        expected_document = self.document_type[document_type]

        if 'mipyme' in document_type:
            values.update({'document_type': expected_document, 'lines': [{'price_unit': 150000}]})
            # We need to define the default value for Optional 27 - Transmission Type
            self.env.company.l10n_ar_fce_transmission_type = 'SCA'

            if '_a' in document_type or '_c' in document_type:
                values.update({'partner': self.partner_mipyme})
            elif '_b' in document_type:
                values.update({'partner': self.partner_mipyme_ex})
        elif '_b' in document_type:
            values.update({'partner': self.partner_cf})

        values.update(forced_values)
        invoice = create_invoice(values)
        self.assertEqual(invoice.l10n_latam_document_type_id.display_name, expected_document.display_name, 'The document should be %s' % expected_document.display_name)
        self._validate_and_review(invoice, expected_result=expected_result)
        return invoice

    def _test_case_credit_note(self, document_type, invoice, data=None, expected_result=None):
        refund = self._create_credit_note(invoice, data=data)
        expected_document = self.document_type[document_type]
        self.assertEqual(refund.l10n_latam_document_type_id.display_name, expected_document.display_name, 'The document should be %s' % expected_document.display_name)
        self._validate_and_review(refund, expected_result=expected_result)
        return refund

    def _test_case_debit_note(self, document_type, invoice, data=None, expected_result='A'):
        debit_note = self._create_debit_note(invoice, data=data)
        expected_document = self.document_type[document_type]
        self.assertEqual(debit_note.l10n_latam_document_type_id.display_name, expected_document.display_name, 'The document should be %s' % expected_document.display_name)
        self._validate_and_review(debit_note, expected_result=expected_result)
        return debit_note

    # Helpers

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

    def _validate_and_review(self, invoice, expected_result=None, error_msg=None):
        """ Validate electronic invoice and review that the invoice has been proper validated """

        expected_result = expected_result or 'A'
        error_msg = error_msg or 'This test return a result different from the expteced (%s)' % expected_result
        self._post(invoice)

        # EDI validations
        self.assertEqual(invoice.l10n_ar_afip_auth_mode, 'CAE', error_msg)
        detail_info = error_msg + '\nReponse\n' + invoice.l10n_ar_afip_xml_response + '\nMsg\n' + invoice.message_ids[0].body
        self.assertEqual(invoice.l10n_ar_afip_result, expected_result, detail_info)

        self.assertTrue(invoice.l10n_ar_afip_auth_code, error_msg)
        self.assertTrue(invoice.l10n_ar_afip_auth_code_due, error_msg)
        self.assertTrue(invoice.l10n_ar_afip_xml_request, error_msg)
        self.assertTrue(invoice.l10n_ar_afip_xml_response, error_msg)


class TestFexCommon(TestEdi):

    @classmethod
    def setUpClass(cls):
        super(TestFexCommon, cls).setUpClass('wsfex')

        cls.partner = cls.res_partner_expresso
        cls.incoterm = cls.env.ref('account.incoterm_EXW')
        cls.journal = cls._create_journal(cls, 'wsfex')

        # Document Types
        cls.document_type.update({
            'invoice_e': cls.env.ref('l10n_ar.dc_e_f'),
            'credit_note_e': cls.env.ref('l10n_ar.dc_e_nc')})

    def _create_invoice_product(self, data=None):
        data = data or {}
        data.update({'incoterm': self.incoterm})
        return super()._create_invoice_product(data=data)

    def _create_invoice_product_service(self, data=None):
        data = data or {}
        data.update({'incoterm': self.incoterm})
        return super()._create_invoice_product_service(data=data)
