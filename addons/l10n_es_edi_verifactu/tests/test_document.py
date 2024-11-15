from unittest import mock

from odoo import _, Command, fields
from odoo.tests import tagged
from .common import TestL10nEsEdiVerifactuCommon

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiVerifactuDocument(TestL10nEsEdiVerifactuCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Use the VAT / NIF that was used to generate the responses
        # This is needed to have the correct record identifiers on the invoices
        cls.company.vat = "A39200019"

    def _check_document(self, document, relevant_expected_response_info):
        if relevant_expected_response_info:
            # Check parsing
            response_info = document.response_info or {}
            self.assertDictEqual(response_info, relevant_expected_response_info | response_info)

            # Check extraction of field values
            self.assertTrue('state' in relevant_expected_response_info)
            self.assertTrue('response_message' in relevant_expected_response_info)
            self.assertTrue('response_time' in relevant_expected_response_info)
            self.assertEqual(document.state, relevant_expected_response_info['state'])
            self.assertEqual(document.response_message, relevant_expected_response_info['response_message'])
            self.assertEqual(document.response_time, fields.Datetime.to_datetime(relevant_expected_response_info['response_time']))

    def _create_dummy_record(self, name=None, invoice_date=None):
        # We do not really care about the values of the record or the generated XML.
        # But we may need a fitting record identifier to extract the information from the response.
        invoice_vals = {
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'date': '2019-01-30',
            'partner_id': self.partner_b.id,  # Spanish customer
            'invoice_line_ids': [
                Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
            ],
        }

        # Adjust some values to give the record the needed record identifier
        if invoice_date is not None:
            invoice_vals['invoice_date'] = invoice_date
        if name is not None:
            # To give the record the needed record identifier
            invoice_vals['name'] = name

        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        return invoice, invoice._l10n_es_edi_verifactu_create_record_document()

    def test_record_identifier(self):
        record, record_document = self._create_dummy_record(name='INV/2019/00006', invoice_date='2024-12-11')
        expected_record_identifier = {
            'IDEmisorFactura': 'A39200019',
            'NumSerieFactura': 'INV/2019/00006',
            'FechaExpedicionFactura': '11-12-2024',
        }
        self.assertDictEqual(record_document.record_identifier,
                             expected_record_identifier | record_document.record_identifier)
        self.assertDictEqual(record.l10n_es_edi_verifactu_record_identifier,
                             expected_record_identifier | record.l10n_es_edi_verifactu_record_identifier)

    def test_generation_error(self):
        _render_xml_node_function = 'odoo.addons.l10n_es_edi_verifactu.models.verifactu_record_mixin.L10nEsEdiVerifactuRecordMixin._l10n_es_edi_verifactu_render_xml_node'
        mock_errors = ["Problem 1", "Problem 2"]
        mock_render_info = {
            'render_vals': None,
            'xml_node': None,
            'errors': mock_errors,
        }
        patched_render_xml_node = mock.patch(_render_xml_node_function, return_value=mock_render_info)
        with patched_render_xml_node:
            record, record_document = self._create_dummy_record()

        expected_record_document_values = {
            'state': 'creating_failed',
            'errors': self._mock_format_record_document_generation_errors(mock_errors),
        }
        self.assertRecordValues(record_document, [expected_record_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': False,
            'l10n_es_edi_verifactu_errors': expected_record_document_values['errors'],
            'l10n_es_edi_verifactu_error_level': 'creating_failed',
        }
        record._compute_l10n_es_edi_verifactu_info_from_record_document_ids()
        self.assertRecordValues(record, [expected_record_values])

    def test_html_response(self):
        # Note: the status code is contained in the content / HTML not in metadata
        #       401: "Certificate not accepted"
        #       403: "Missing certificate in request"
        record, record_document = self._create_dummy_record()
        document = record_document._create_batch_document()
        response = self._mock_response(200,'l10n_es_edi_verifactu/tests/responses/certificate_issue.html', content_type='text/html')
        with self._mock_request(response):
            document._send()

        relevant_expected_parse_info = {
            'content_type': 'HTML',
            'response_message': response.text,
            'response_time': "2024-12-05 00:00:00",
            'state': 'rejected',
            'document_type': 'batch',
            'errors': [
                'The document could not be sent; the access was denied: <main class="col-12 col-lg-7" id="acc-main"> <div class="d-flex">\n<i class="aeat-ico fa-ico-error-sm ico-size-4 mr-3 text-danger" aria-hidden="true" role="presentation"></i><h1 id="js-nombre-canal" class="font-weight-bold mb-0 display-4 mb-3 text-danger">401</h1>\n</div>\n<p>No autorizado. Se ha producido un error al verificar el certificado presentado. Las causas m&#225;s probables de este error son:</p>\n<ul>\n<li>El certificado no ha sido firmado por una autoridad reconocida.</li>\n<li>El tipo de certificado no es v&#225;lido para el servicio al que se quiere acceder.</li>\n<li>El certificado ha expirado.</li>\n</ul>\n<p>Puede contactar con el servicio de atenci&#243;n al contribuyente indicando el c&#243;digo de error 401.</p>\n<a target="_self" title="Comunicar incidencia" href="https://www2.agenciatributaria.gob.es/soporteaeat/Formularios.nsf/soporteOnline.php?OpenForm&amp;codigoError=401" class="d-block">Comunicar incidencia</a></main> \n',
            ],
            'record_info': {},
        }
        self._check_document(document, relevant_expected_parse_info)

        expected_record_document_values = {
            'state': 'rejected',
            'errors': self._mock_format_record_document_response_document_errors(relevant_expected_parse_info['errors']),
        }
        self.assertRecordValues(record_document, [expected_record_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': 'rejected',
            'l10n_es_edi_verifactu_errors': expected_record_document_values['errors'],
            'l10n_es_edi_verifactu_error_level': 'rejected',
        }
        record._compute_l10n_es_edi_verifactu_info_from_record_document_ids()
        self.assertRecordValues(record, [expected_record_values])

    def test_soapfault(self):
        record, record_document = self._create_dummy_record()
        document = record_document._create_batch_document()
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/soapfault.xml')
        with self._mock_request(response):
            document._send()

        relevant_expected_parse_info = {
            'content_type': 'XML',
            'response_message': response.text,
            'response_time': "2024-12-05 00:00:00",
            'state': 'rejected',
            'document_type': 'batch',
            'errors': [
                'The document was rejected by the AEAT: [env:Client] Codigo[4102].El XML no cumple el esquema. Falta informar campo obligatorio.: NombreRazon',
            ],
            'record_info': {},
        }
        self._check_document(document, relevant_expected_parse_info)

        expected_record_document_values = {
            'state': 'rejected',
            'errors': self._mock_format_record_document_response_document_errors(relevant_expected_parse_info['errors']),
        }
        self.assertRecordValues(record_document, [expected_record_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': 'rejected',
            'l10n_es_edi_verifactu_errors': expected_record_document_values['errors'],
            'l10n_es_edi_verifactu_error_level': 'rejected',
        }
        record._compute_l10n_es_edi_verifactu_info_from_record_document_ids()
        self.assertRecordValues(record, [expected_record_values])

    def test_batch_single_accepted_registration(self):
        record, record_document = self._create_dummy_record(name='INV/2019/00026', invoice_date='2024-12-30')
        document = record_document._create_batch_document()
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_accepted_registration.xml')
        with self._mock_request(response):
            document._send()

        relevant_expected_parse_info = {
            'content_type': 'XML',
            'response_message': response.text,
            'response_time': "2024-12-05 00:00:00",
            'state': 'accepted',
            'waiting_time_seconds': 60,
            'document_type': 'batch',
            'errors': [],
            'record_info': {
                "('A39200019', 'INV/2019/00026')": {
                    'state': 'accepted',
                    'cancellation': False,
                    'errors': [],
                },
            },
        }
        self._check_document(document, relevant_expected_parse_info)

        expected_record_document_values = {
            'state': 'accepted',
            'errors': False,
        }
        self.assertRecordValues(record_document, [expected_record_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': 'accepted',
            'l10n_es_edi_verifactu_errors': '',
            'l10n_es_edi_verifactu_error_level': False,
        }
        record._compute_l10n_es_edi_verifactu_info_from_record_document_ids()
        self.assertRecordValues(record, [expected_record_values])

    def test_batch_single_rejected_registration(self):
        record, record_document = self._create_dummy_record(name='INV/2019/00006', invoice_date='2024-12-11')

        document = record_document._create_batch_document()
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_rejected_registration.xml')
        with self._mock_request(response):
            document._send()

        record_info = {
            'state': 'rejected',
            'cancellation': False,
            'errors': [
                '[1244] El campo FechaHoraHusoGenRegistro tiene un formato incorrecto.',
            ],
        }
        relevant_expected_parse_info = {
            'content_type': 'XML',
            'response_message': response.text,
            'response_time': "2024-12-05 00:00:00",
            'state': 'rejected',
            'waiting_time_seconds': 60,
            'document_type': 'batch',
            'errors': [],
            'record_info': {
                "('A39200019', 'INV/2019/00006')": record_info,
            },
        }
        self._check_document(document, relevant_expected_parse_info)

        expected_record_document_values = {
            'state': 'rejected',
            'errors': self._mock_format_record_document_response_record_errors(record_info['errors']),
        }
        self.assertRecordValues(record_document, [expected_record_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': 'rejected',
            'l10n_es_edi_verifactu_errors': expected_record_document_values['errors'],
            'l10n_es_edi_verifactu_error_level': 'rejected',
        }
        record._compute_l10n_es_edi_verifactu_info_from_record_document_ids()
        self.assertRecordValues(record, [expected_record_values])

    def test_batch_single_registered_with_errors_registration(self):
        record, record_document = self._create_dummy_record(name='INV/2019/00007', invoice_date='2024-12-17')
        document = record_document._create_batch_document()
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_registered_with_errors_registration.xml')
        with self._mock_request(response):
            document._send()

        record_info = {
            'state': 'registered_with_errors',
            'cancellation': False,
            'errors': [
                '[2005] El campo ImporteTotal tiene un valor incorrecto para el valor de los campos BaseImponibleOimporteNoSujeto, CuotaRepercutida y CuotaRecargoEquivalencia suministrados.',
            ],
        }
        relevant_expected_parse_info = {
            'content_type': 'XML',
            'response_message': response.text,
            'response_time': "2024-12-05 00:00:00",
            'state': 'registered_with_errors',
            'waiting_time_seconds': 60,
            'document_type': 'batch',
            'errors': [],
            'record_info': {
                "('A39200019', 'INV/2019/00007')": record_info,
            },
        }
        self._check_document(document, relevant_expected_parse_info)

        expected_record_document_values = {
            'state': 'registered_with_errors',
            'errors': self._mock_format_record_document_response_record_errors(record_info['errors']),
        }
        self.assertRecordValues(record_document, [expected_record_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': 'registered_with_errors',
            'l10n_es_edi_verifactu_errors': expected_record_document_values['errors'],
            'l10n_es_edi_verifactu_error_level': 'registered_with_errors',
        }
        record._compute_l10n_es_edi_verifactu_info_from_record_document_ids()
        self.assertRecordValues(record, [expected_record_values])

    def test_response_parsing_error_record_document_not_found(self):
        record, record_document = self._create_dummy_record(name='INV/2019/00500', invoice_date='2024-12-17')
        document = record_document._create_batch_document()
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_registered_with_errors_registration.xml')
        with self._mock_request(response):
            document._send()

        record_info = {
            'state': 'registered_with_errors',
            'cancellation': False,
            'errors': [
                '[2005] El campo ImporteTotal tiene un valor incorrecto para el valor de los campos BaseImponibleOimporteNoSujeto, CuotaRepercutida y CuotaRecargoEquivalencia suministrados.',
            ],
        }
        relevant_expected_parse_info = {
            'content_type': 'XML',
            'response_message': response.text,
            'response_time': "2024-12-05 00:00:00",
            'state': 'registered_with_errors',
            'waiting_time_seconds': 60,
            'document_type': 'batch',
            'errors': [],
            'record_info': {
                "('A39200019', 'INV/2019/00007')": record_info,  # Note: it is different than the record values
            },
        }
        self._check_document(document, relevant_expected_parse_info)

        errors = [_("We could not find any information about the record in the linked batch document.")]
        expected_record_document_values = {
            'state': 'parsing_failed',
            'errors': self._mock_format_record_document_response_parsing_errors(errors),
        }
        self.assertRecordValues(record_document, [expected_record_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': 'parsing_failed',
            'l10n_es_edi_verifactu_errors': expected_record_document_values['errors'],
            'l10n_es_edi_verifactu_error_level': 'parsing_failed',
        }
        record._compute_l10n_es_edi_verifactu_info_from_record_document_ids()
        self.assertRecordValues(record, [expected_record_values])
