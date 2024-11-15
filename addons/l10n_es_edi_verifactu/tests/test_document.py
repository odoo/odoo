import requests
from unittest.mock import Mock

from odoo.tests import tagged
from .common import TestEsEdiVerifactuCommon

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEsEdiVerifactuDocument(TestEsEdiVerifactuCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def _mock_response(self, status_code, response_file, content_type='text/xml;charset=UTF-8'):
        response = Mock(spec=requests.Response)
        response.status_code = status_code
        response.text = self._read_file(response_file)
        response.headers = {
            'content-type': content_type,
        }
        return response

    def test_html_response(self):
        response = self._mock_response(200,'l10n_es_edi_verifactu/tests/responses/certificate_issue.html', content_type='text/html')
        for document_type in ['batch', 'query']:
            with self.subTest(f"document_type = {document_type}"):
                parse_info = self.env['l10n_es_edi_verifactu.response_parser']._parse_response(response, document_type=document_type)
                self.assertEqual(parse_info['content_type'], 'HTML')
                self.assertEqual(parse_info['state'], 'rejected')
        # Note: the status code is contained in the content / HTML not in metadata
        #       401: "Certificate not accepted"
        #       403: "Missing certificate in request"
        self.assertEqual(True, False, "TODO: finish test implementation.")

    def test_soapfault(self):
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/soapfault.xml')
        for document_type in ['batch', 'query']:
            with self.subTest(f"document_type = {document_type}"):
                parse_info = self.env['l10n_es_edi_verifactu.response_parser']._parse_response(response, document_type=document_type)
                self.assertEqual(parse_info['content_type'], 'XML')
                self.assertEqual(parse_info['state'], 'rejected')
        self.assertEqual(True, False, "TODO: finish test implementation.")

    def test_batch_single_accepted_registration(self):
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_accepted_registration.xml')
        parse_info = self.env['l10n_es_edi_verifactu.response_parser']._parse_response(response, document_type='batch')
        self.assertEqual(parse_info['content_type'], 'XML')
        self.assertEqual(parse_info['state'], 'accepted')
        self.assertEqual(parse_info['waiting_time_seconds'], 60)
        self.assertEqual(True, False, "TODO: finish test implementation.")

    def test_batch_single_rejected_registration(self):
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_rejected_registration.xml')
        parse_info = self.env['l10n_es_edi_verifactu.response_parser']._parse_response(response, document_type='batch')
        self.assertEqual(parse_info['content_type'], 'XML')
        self.assertEqual(parse_info['state'], 'rejected')
        self.assertEqual(parse_info['waiting_time_seconds'], 60)
        self.assertEqual(True, False, "TODO: finish test implementation.")

    def test_batch_single_registered_with_errors_registration(self):
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_registered_with_errors_registration.xml')
        parse_info = self.env['l10n_es_edi_verifactu.response_parser']._parse_response(response, document_type='batch')
        self.assertEqual(parse_info['content_type'], 'XML')
        self.assertEqual(parse_info['state'], 'registered_with_errors')
        self.assertEqual(parse_info['waiting_time_seconds'], 60)
        self.assertEqual(True, False, "TODO: finish test implementation.")

    def test_batch_registered_with_errors_one_of_everything(self):
        self.assertEqual(True, False, "TODO: Test not implemented yet.")
