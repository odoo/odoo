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
        # Note: the status code is contained in the content / HTML not in metadata
        #       401: "Certificate not accepted"
        #       403: "Missing certificate in request"
        response = self._mock_response(200,'l10n_es_edi_verifactu/tests/responses/certificate_issue.html', content_type='text/html')
        for document_type in ['batch', 'query']:
            with self.subTest(f"document_type = {document_type}"):
                parse_info = self.env['l10n_es_edi_verifactu.response_parser']._parse_response(response, document_type=document_type)
                relevant_expected_parse_info = {
                    'content_type': 'HTML',
                    'state': 'rejected',
                    'document_type': document_type,
                    'errors': [
                        'access_denied: <main class="col-12 col-lg-7" id="acc-main"> <div class="d-flex">\n<i class="aeat-ico fa-ico-error-sm ico-size-4 mr-3 text-danger" aria-hidden="true" role="presentation"></i><h1 id="js-nombre-canal" class="font-weight-bold mb-0 display-4 mb-3 text-danger">401</h1>\n</div>\n<p>No autorizado. Se ha producido un error al verificar el certificado presentado. Las causas m&#225;s probables de este error son:</p>\n<ul>\n<li>El certificado no ha sido firmado por una autoridad reconocida.</li>\n<li>El tipo de certificado no es v&#225;lido para el servicio al que se quiere acceder.</li>\n<li>El certificado ha expirado.</li>\n</ul>\n<p>Puede contactar con el servicio de atenci&#243;n al contribuyente indicando el c&#243;digo de error 401.</p>\n<a target="_self" title="Comunicar incidencia" href="https://www2.agenciatributaria.gob.es/soporteaeat/Formularios.nsf/soporteOnline.php?OpenForm&amp;codigoError=401" class="d-block">Comunicar incidencia</a></main> \n'
                    ],
                    'record_info': {
                        None: {'errors': []}
                    },
                }
                self.assertDictEqual(parse_info, relevant_expected_parse_info | parse_info)

    def test_soapfault(self):
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/soapfault.xml')
        for document_type in ['batch', 'query']:
            with self.subTest(f"document_type = {document_type}"):
                parse_info = self.env['l10n_es_edi_verifactu.response_parser']._parse_response(response, document_type=document_type)
                relevant_expected_parse_info = {
                    'content_type': 'XML',
                    'state': 'rejected',
                    'document_type': document_type,
                    'errors': [
                        'Codigo[4102].El XML no cumple el esquema. Falta informar campo obligatorio.: NombreRazon'
                    ],
                    'record_info': {
                        None: {'errors': []}
                    },
                }
                self.assertDictEqual(parse_info, relevant_expected_parse_info | parse_info)

    def test_batch_single_accepted_registration(self):
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_accepted_registration.xml')
        parse_info = self.env['l10n_es_edi_verifactu.response_parser']._parse_response(response, document_type='batch')
        relevant_expected_parse_info = {
            'content_type': 'XML',
            'state': 'accepted',
            'waiting_time_seconds': 60,
            'document_type': 'batch',
            'errors': [],
            'record_info': {
                "('A39200019', 'INV/2024/00026')": {
                    'state': 'accepted',
                    'cancellation': False,
                    'errors': []
                },
                None: {'errors': []}
            },
        }
        self.assertDictEqual(parse_info, relevant_expected_parse_info | parse_info)

    def test_batch_single_rejected_registration(self):
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_rejected_registration.xml')
        parse_info = self.env['l10n_es_edi_verifactu.response_parser']._parse_response(response, document_type='batch')
        relevant_expected_parse_info = {
            'content_type': 'XML',
            'state': 'rejected',
            'waiting_time_seconds': 60,
            'document_type': 'batch',
            'errors': [],
            'record_info': {
                "('A39200019', 'INV/2024/00006')": {
                    'state': 'rejected',
                    'cancellation': False,
                    'errors': [
                        '[1244] El campo FechaHoraHusoGenRegistro tiene un formato incorrecto.'
                    ]
                },
                None: {'errors': []}
            },
        }
        self.assertDictEqual(parse_info, relevant_expected_parse_info | parse_info)

    def test_batch_single_registered_with_errors_registration(self):
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_registered_with_errors_registration.xml')
        parse_info = self.env['l10n_es_edi_verifactu.response_parser']._parse_response(response, document_type='batch')
        relevant_expected_parse_info = {
            'content_type': 'XML',
            'state': 'registered_with_errors',
            'waiting_time_seconds': 60,
            'document_type': 'batch',
            'errors': [],
            'record_info': {
                "('A39200019', 'INV/2024/00007')": {
                    'state': 'registered_with_errors',
                    'cancellation': False,
                    'errors': [
                        '[2005] El campo ImporteTotal tiene un valor incorrecto para el valor de los campos BaseImponibleOimporteNoSujeto, CuotaRepercutida y CuotaRecargoEquivalencia suministrados.'
                    ]
                },
                None: {'errors': []}
            },
        }
        self.assertDictEqual(parse_info, relevant_expected_parse_info | parse_info)
