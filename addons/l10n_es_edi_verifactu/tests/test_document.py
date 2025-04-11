import datetime
from unittest import mock

from odoo import _, Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from .common import TestL10nEsEdiVerifactuCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiVerifactuDocument(TestL10nEsEdiVerifactuCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Use the VAT / NIF that was used to generate the responses
        # This is needed to have the correct record identifiers on the invoices
        cls.company.vat = 'A39200019'

    def _create_dummy_invoice(self, name=None, invoice_date=None):
        # The only values we care about are the ones relevant for the record identifier.
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
            invoice_vals['name'] = name

        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()

        return invoice

    def test_record_identifier(self):
        invoice = self._create_dummy_invoice(name='INV/2019/00006', invoice_date='2024-12-11')
        document = self.env['l10n_es_edi_verifactu.document']._create_for_record(invoice)
        expected_record_identifier = {
            'IDEmisorFactura': 'A39200019',
            'NumSerieFactura': 'INV/2019/00006',
            'FechaExpedicionFactura': '11-12-2024',
        }
        record_identifier = document.record_identifier
        self.assertDictEqual(record_identifier, expected_record_identifier | record_identifier)
        record_identifier = invoice._l10n_es_edi_verifactu_record_identifier()
        self.assertDictEqual(record_identifier, expected_record_identifier | record_identifier)

    def test_cannot_delete_chained_document(self):
        invoice = self._create_dummy_invoice(name='INV/2019/00006', invoice_date='2024-12-11')
        document = self.env['l10n_es_edi_verifactu.document']._create_for_record(invoice)
        with self.assertRaises(UserError):
            document.unlink()

    def test_generation_error(self):
        render_xml_node_function_path = 'odoo.addons.l10n_es_edi_verifactu.models.verifactu_document.L10nEsEdiVerifactuDocument._render_xml_node'
        mock_errors = ["Problem 1", "Problem 2"]
        mock_render_info = {
            'render_vals': None,
            'xml_node': None,
            'errors': mock_errors,
        }
        patched_render_xml_node = mock.patch(render_xml_node_function_path, return_value=mock_render_info)
        invoice = self._create_dummy_invoice()
        with patched_render_xml_node:
            document = self.env['l10n_es_edi_verifactu.document']._create_for_record(invoice)

        expected_document_values = {
            'document_type': 'submission',
            'state': False,
            'errors': self._mock_format_document_generation_errors(["Problem 1", "Problem 2"]),
            'response_time': False,
            'response_csv': False,
        }
        self.assertRecordValues(document, [expected_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': False,
            'l10n_es_edi_verifactu_errors': expected_document_values['errors'],
            'l10n_es_edi_verifactu_error_level': False,
        }
        invoice._compute_l10n_es_edi_verifactu_info_from_document_ids()
        self.assertRecordValues(invoice, [expected_record_values])

    def test_html_response(self):
        # Note: the status code is contained in the content / HTML not in metadata
        #       401: "Certificate not accepted"
        #       403: "Missing certificate in request"
        invoice = self._create_dummy_invoice()
        document = self.env['l10n_es_edi_verifactu.document']._create_for_record(invoice)
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/certificate_issue.html', content_type='text/html')
        with self._mock_request(response):
            _batch_xml, info = document._send_as_batch()

        expected_response_info = {
            'content_type': 'HTML',
            'response_time': '2024-12-05 00:00:00',
            'errors': [
                'The document could not be sent; the access was denied: <main class="col-12 col-lg-7" id="acc-main"> <div class="d-flex">\n<i class="aeat-ico fa-ico-error-sm ico-size-4 mr-3 text-danger" aria-hidden="true" role="presentation"></i><h1 id="js-nombre-canal" class="font-weight-bold mb-0 display-4 mb-3 text-danger">401</h1>\n</div>\n<p>No autorizado. Se ha producido un error al verificar el certificado presentado. Las causas m&#225;s probables de este error son:</p>\n<ul>\n<li>El certificado no ha sido firmado por una autoridad reconocida.</li>\n<li>El tipo de certificado no es v&#225;lido para el servicio al que se quiere acceder.</li>\n<li>El certificado ha expirado.</li>\n</ul>\n<p>Puede contactar con el servicio de atenci&#243;n al contribuyente indicando el c&#243;digo de error 401.</p>\n<a target="_self" title="Comunicar incidencia" href="https://www2.agenciatributaria.gob.es/soporteaeat/Formularios.nsf/soporteOnline.php?OpenForm&amp;codigoError=401" class="d-block">Comunicar incidencia</a></main> \n',
            ],
            'record_info': {},
        }
        self.assertDictEqual(info, expected_response_info | info)

        self.assertFalse(self.company.l10n_es_edi_verifactu_next_batch_time)

        expected_document_values = {
            'document_type': 'submission',
            'response_time': self.fakenow,
            'response_csv': False,
            'state': False,
            'errors': self._mock_format_document_generic_errors(expected_response_info['errors']),
        }
        self.assertRecordValues(document, [expected_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': False,
            'l10n_es_edi_verifactu_errors': expected_document_values['errors'],
            'l10n_es_edi_verifactu_error_level': False,
        }
        invoice._compute_l10n_es_edi_verifactu_info_from_document_ids()
        self.assertRecordValues(invoice, [expected_record_values])

    def test_soapfault(self):
        invoice = self._create_dummy_invoice()
        document = self.env['l10n_es_edi_verifactu.document']._create_for_record(invoice)

        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/soapfault.xml')
        with self._mock_request(response):
            _batch_xml, info = document._send_as_batch()

        expected_response_info = {
            'content_type': 'XML',
            'response_time': '2024-12-05 00:00:00',
            'state': 'rejected',
            'errors': [
                '[env:Client] Codigo[4102].El XML no cumple el esquema. Falta informar campo obligatorio.: NombreRazon',
            ],
            'record_info': {},
        }
        self.assertDictEqual(info, expected_response_info | info)

        self.assertFalse(self.company.l10n_es_edi_verifactu_next_batch_time)

        expected_document_values = {
            'document_type': 'submission',
            'response_time': self.fakenow,
            'response_csv': False,
            'state': 'rejected',
            'errors': self._mock_format_document_aeat_errors(expected_response_info['errors']),
        }
        self.assertRecordValues(document, [expected_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': 'rejected',
            'l10n_es_edi_verifactu_errors': expected_document_values['errors'],
            'l10n_es_edi_verifactu_error_level': 'rejected',
        }
        invoice._compute_l10n_es_edi_verifactu_info_from_document_ids()
        self.assertRecordValues(invoice, [expected_record_values])

    def test_batch_single_accepted_registration(self):
        invoice = self._create_dummy_invoice(name='INV/2019/00026', invoice_date='2024-12-30')
        document = self.env['l10n_es_edi_verifactu.document']._create_for_record(invoice)
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_accepted_registration.xml')
        with self._mock_request(response):
            _batch_xml, info = document._send_as_batch()

        expected_response_info = {
            'content_type': 'XML',
            'response_time': '2024-12-05 00:00:00',
            'state': 'accepted',
            'response_csv': 'A-YDSW8NLFLANWPM',
            'waiting_time_seconds': 60,
            'errors': [],
            'record_info': {
                "('A39200019', 'INV/2019/00026')": {
                    'state': 'accepted',
                    'cancellation': False,
                    'errors': [],
                },
            },
        }
        self.assertDictEqual(info, expected_response_info | info)

        self.assertEqual(self.company.l10n_es_edi_verifactu_next_batch_time,
                         datetime.datetime(2024, 12, 5, 0, 1, 0))

        expected_document_values = {
            'document_type': 'submission',
            'response_time': self.fakenow,
            'response_csv': 'A-YDSW8NLFLANWPM',
            'state': 'accepted',
            'errors': False,
        }
        self.assertRecordValues(document, [expected_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': 'accepted',
            'l10n_es_edi_verifactu_errors': '',
            'l10n_es_edi_verifactu_error_level': False,
        }
        invoice._compute_l10n_es_edi_verifactu_info_from_document_ids()
        self.assertRecordValues(invoice, [expected_record_values])

    def test_batch_single_rejected_registration(self):
        invoice = self._create_dummy_invoice(name='INV/2019/00006', invoice_date='2024-12-11')
        document = self.env['l10n_es_edi_verifactu.document']._create_for_record(invoice)
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_rejected_registration.xml')
        with self._mock_request(response):
            _batch_xml, info = document._send_as_batch()

        record_info = {
            'state': 'rejected',
            'cancellation': False,
            'errors': [
                '[1244] El campo FechaHoraHusoGenRegistro tiene un formato incorrecto.',
            ],
        }
        expected_response_info = {
            'content_type': 'XML',
            'response_time': '2024-12-05 00:00:00',
            'state': 'rejected',
            'response_csv': False,
            'waiting_time_seconds': 60,
            'errors': [],
            'record_info': {
                "('A39200019', 'INV/2019/00006')": record_info,
            },
        }
        self.assertDictEqual(info, expected_response_info | info)

        self.assertEqual(self.company.l10n_es_edi_verifactu_next_batch_time,
                         datetime.datetime(2024, 12, 5, 0, 1, 0))

        expected_document_values = {
            'document_type': 'submission',
            'response_time': self.fakenow,
            'response_csv': False,
            'state': 'rejected',
            'errors': self._mock_format_document_aeat_errors(record_info['errors']),
        }
        self.assertRecordValues(document, [expected_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': 'rejected',
            'l10n_es_edi_verifactu_errors': expected_document_values['errors'],
            'l10n_es_edi_verifactu_error_level': 'rejected',
        }
        invoice._compute_l10n_es_edi_verifactu_info_from_document_ids()
        self.assertRecordValues(invoice, [expected_record_values])

    def test_batch_single_registered_with_errors_registration(self):
        invoice = self._create_dummy_invoice(name='INV/2019/00007', invoice_date='2024-12-17')
        document = self.env['l10n_es_edi_verifactu.document']._create_for_record(invoice)
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_registered_with_errors_registration.xml')
        with self._mock_request(response):
            _batch_xml, info = document._send_as_batch()

        record_info = {
            'state': 'registered_with_errors',
            'cancellation': False,
            'errors': [
                '[2005] El campo ImporteTotal tiene un valor incorrecto para el valor de los campos BaseImponibleOimporteNoSujeto, CuotaRepercutida y CuotaRecargoEquivalencia suministrados.',
            ],
        }
        expected_response_info = {
            'content_type': 'XML',
            'response_time': '2024-12-05 00:00:00',
            'state': 'registered_with_errors',
            'response_csv': 'A-X2CPJ3HE3AFADY',
            'waiting_time_seconds': 60,
            'errors': [],
            'record_info': {
                "('A39200019', 'INV/2019/00007')": record_info,
            },
        }
        self.assertDictEqual(info, expected_response_info | info)

        self.assertEqual(self.company.l10n_es_edi_verifactu_next_batch_time,
                         datetime.datetime(2024, 12, 5, 0, 1, 0))

        expected_document_values = {
            'document_type': 'submission',
            'response_time': self.fakenow,
            'response_csv': 'A-X2CPJ3HE3AFADY',
            'state': 'registered_with_errors',
            'errors': self._mock_format_document_aeat_errors(record_info['errors']),
        }
        self.assertRecordValues(document, [expected_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': 'registered_with_errors',
            'l10n_es_edi_verifactu_errors': expected_document_values['errors'],
            'l10n_es_edi_verifactu_error_level': 'registered_with_errors',
        }
        invoice._compute_l10n_es_edi_verifactu_info_from_document_ids()
        self.assertRecordValues(invoice, [expected_record_values])

    def test_response_parsing_error_document_not_found(self):
        invoice = self._create_dummy_invoice(name='INV/2019/00500', invoice_date='2024-12-17')
        document = self.env['l10n_es_edi_verifactu.document']._create_for_record(invoice)
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_registered_with_errors_registration.xml')
        with self._mock_request(response):
            _batch_xml, info = document._send_as_batch()

        record_info = {
            'state': 'registered_with_errors',
            'cancellation': False,
            'errors': [
                '[2005] El campo ImporteTotal tiene un valor incorrecto para el valor de los campos BaseImponibleOimporteNoSujeto, CuotaRepercutida y CuotaRecargoEquivalencia suministrados.',
            ],
        }
        expected_response_info = {
            'content_type': 'XML',
            'response_time': '2024-12-05 00:00:00',
            'state': 'registered_with_errors',
            'waiting_time_seconds': 60,
            'errors': [],
            'record_info': {
                "('A39200019', 'INV/2019/00007')": record_info,  # Note: it is different than the record values
            },
        }
        self.assertDictEqual(info, expected_response_info | info)

        # Since we received a "waiting time" we still update the time for the next batch
        self.assertEqual(self.company.l10n_es_edi_verifactu_next_batch_time,
                         datetime.datetime(2024, 12, 5, 0, 1, 0))

        errors = [_("We could not find any information about the record in the linked batch document.")]
        expected_document_values = {
            'document_type': 'submission',
            'response_time': self.fakenow,
            'response_csv': 'A-X2CPJ3HE3AFADY',
            'state': False,
            'errors': self._mock_format_document_generic_errors(errors),
        }
        self.assertRecordValues(document, [expected_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': False,
            'l10n_es_edi_verifactu_errors': expected_document_values['errors'],
            'l10n_es_edi_verifactu_error_level': False,
        }
        invoice._compute_l10n_es_edi_verifactu_info_from_document_ids()
        self.assertRecordValues(invoice, [expected_record_values])

    def test_mark_records_for_next_batch(self):
        # Check that we can send immediately
        self.assertFalse(self.company.l10n_es_edi_verifactu_next_batch_time)

        invoice = self._create_dummy_invoice(name='INV/2019/00026', invoice_date='2024-12-30')
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_accepted_registration.xml')
        with self._mock_request(response):
            created_documents = self.env['l10n_es_edi_verifactu.document'].mark_records_for_next_batch(invoice)
        document = created_documents[invoice]

        expected_document_values = {
            'document_type': 'submission',
            'state': 'accepted',
            'errors': False,
            'response_time': self.fakenow,
            'response_csv': 'A-YDSW8NLFLANWPM',
        }
        self.assertRecordValues(document, [expected_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': 'accepted',
            'l10n_es_edi_verifactu_errors': '',
            'l10n_es_edi_verifactu_error_level': False,
        }
        invoice._compute_l10n_es_edi_verifactu_info_from_document_ids()
        self.assertRecordValues(invoice, [expected_record_values])

        # The last response indicated a waiting time of 60 seconds.
        # So the next batch should only be sent at self.fakenow + 60s
        self.assertEqual(self.company.l10n_es_edi_verifactu_next_batch_time,
                         datetime.datetime(2024, 12, 5, 0, 1, 0))

        # Try to send another invoice. Now we should not be able to send immediately.
        # Check that the cron will later be called again at the right time
        # (by checking that the trigger function was called with the right time).

        invoice = self._create_dummy_invoice(name='INV/2019/00027', invoice_date='2024-12-30')
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/batch_single_accepted_registration.xml')
        cron_trigger_result_dict = {}
        with self._mock_request(response), self._mock_cron_trigger(cron_trigger_result_dict):
            created_documents = self.env['l10n_es_edi_verifactu.document'].mark_records_for_next_batch(invoice)
        document = created_documents[invoice]
        self.assertEqual(cron_trigger_result_dict['at'], datetime.datetime(2024, 12, 5, 0, 1, 0))

        expected_document_values = {
            'document_type': 'submission',
            'response_time': False,
            'response_csv': False,
            'state': False,
            'errors': False,
        }
        self.assertRecordValues(document, [expected_document_values])

    def test_response_issue(self):
        # We can send immediately
        self.assertFalse(self.company.l10n_es_edi_verifactu_next_batch_time)

        # Note: The record identifier of `invoice` is different than the one found in the response
        invoice = self._create_dummy_invoice(name='INV/2019/00500', invoice_date='2024-12-17')
        response = self._mock_response(200, 'l10n_es_edi_verifactu/tests/responses/certificate_issue.html', content_type='text/html')
        cron_trigger_result_dict = {}
        with self._mock_request(response), self._mock_cron_trigger(cron_trigger_result_dict):
            created_documents = self.env['l10n_es_edi_verifactu.document'].mark_records_for_next_batch(invoice)
        document = created_documents[invoice]

        # We failed to send the document and there was no waiting time in the response since we got an access denied error
        self.assertFalse(document.state)
        self.assertFalse(self.company.l10n_es_edi_verifactu_next_batch_time)
        # So the cron has to be retriggered
        self.assertEqual(cron_trigger_result_dict['at'], datetime.datetime(2024, 12, 5, 0, 1, 0))
