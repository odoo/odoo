import datetime
from unittest import mock

from odoo import _, Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import zeep
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
        document = invoice._l10n_es_edi_verifactu_create_document()
        expected_record_identifier = {
            'IDEmisorFactura': 'A39200019',
            'NumSerieFactura': 'INV/2019/00006',
            'FechaExpedicionFactura': '11-12-2024',
        }
        record_identifier = document.record_identifier
        self.assertDictEqual(record_identifier, expected_record_identifier | record_identifier)

    def test_cannot_delete_chained_document(self):
        invoice = self._create_dummy_invoice(name='INV/2019/00006', invoice_date='2024-12-11')
        document = invoice._l10n_es_edi_verifactu_create_document()
        with self.assertRaises(UserError):
            document.unlink()

    def test_generation_error(self):
        # TODO: mock error check function instead
        render_xml_node_function_path = 'odoo.addons.l10n_es_edi_verifactu.models.verifactu_document.L10nEsEdiVerifactuDocument._check_record_values'
        mock_errors = ["Problem 1", "Problem 2"]
        patched_render_xml_node = mock.patch(render_xml_node_function_path, return_value=mock_errors)
        invoice = self._create_dummy_invoice()
        with patched_render_xml_node:
            document = invoice._l10n_es_edi_verifactu_create_document()

        expected_document_values = {
            'document_type': 'submission',
            'state': False,
            'errors': self._mock_format_document_generation_errors(mock_errors),
            'response_csv': False,
        }
        self.assertRecordValues(document, [expected_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': False,
            'l10n_es_edi_verifactu_errors': expected_document_values['errors'],
            'l10n_es_edi_verifactu_error_level': False,
        }
        self.assertRecordValues(invoice, [expected_record_values])

    def test_html_response(self):
        # TODO: rename test; or maybe test for doctype html header?
        invoice = self._create_dummy_invoice()
        document = invoice._l10n_es_edi_verifactu_create_document()
        with self._mock_zeep_registration_operation_certificate_issue():
            _batch_xml, info = document._send_as_batch()

        expected_response_info = {
            'errors': ["The document could not be sent; the access was denied due to a problem with the certificate."],
            'record_info': {},
        }
        self.assertDictEqual(info, expected_response_info | info)

        self.assertFalse(self.company.l10n_es_edi_verifactu_next_batch_time)

        expected_document_values = {
            'document_type': 'submission',
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
        self.assertRecordValues(invoice, [expected_record_values])

    def test_soapfault(self):
        def _raise_soapfault(*args, **kwargs):
            message = "Codigo[4102].El XML no cumple el esquema. Falta informar campo obligatorio.: NombreRazon"
            code = "env:Client"
            raise zeep.exceptions.Fault(message, code=code)

        invoice = self._create_dummy_invoice()
        document = invoice._l10n_es_edi_verifactu_create_document()
        with self._mock_zeep_registration_operation_function(_raise_soapfault):
            _batch_xml, info = document._send_as_batch()

        expected_response_info = {
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
        self.assertRecordValues(invoice, [expected_record_values])

    def test_batch_single_accepted_registration(self):
        invoice = self._create_dummy_invoice(name='INV/2019/00026', invoice_date='2024-12-30')
        document = invoice._l10n_es_edi_verifactu_create_document()
        with self._mock_zeep_registration_operation('l10n_es_edi_verifactu/tests/responses/batch_single_accepted_registration.json'):
            _batch_xml, info = document._send_as_batch()

        expected_response_info = {
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
        self.assertRecordValues(invoice, [expected_record_values])

    def test_batch_single_accepted_cancellation(self):
        invoice = self._create_dummy_invoice(name='INV/2019/00047', invoice_date='2024-12-30')
        document = invoice._l10n_es_edi_verifactu_create_document(cancellation=True)
        with self._mock_zeep_registration_operation('l10n_es_edi_verifactu/tests/responses/batch_single_accepted_cancellation.json'):
            _batch_xml, info = document._send_as_batch()

        expected_response_info = {
            'state': 'accepted',
            'response_csv': 'A-JJ2XWTUCTVV3TQ',
            'waiting_time_seconds': 60,
            'errors': [],
            'record_info': {
                "('A39200019', 'INV/2019/00047')": {
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
            'document_type': 'cancellation',
            'response_csv': 'A-JJ2XWTUCTVV3TQ',
            'state': 'accepted',
            'errors': False,
        }
        self.assertRecordValues(document, [expected_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': 'cancelled',
            'l10n_es_edi_verifactu_errors': '',
            'l10n_es_edi_verifactu_error_level': False,
            'state': 'cancel',  # The Veri*Factu cancellation cancels the move
        }
        self.assertRecordValues(invoice, [expected_record_values])

    def test_batch_single_rejected_registration(self):
        invoice = self._create_dummy_invoice(name='INV/2019/00006', invoice_date='2024-12-11')
        document = invoice._l10n_es_edi_verifactu_create_document()
        with self._mock_zeep_registration_operation('l10n_es_edi_verifactu/tests/responses/batch_single_rejected_registration.json'):
            _batch_xml, info = document._send_as_batch()

        record_info = {
            'state': 'rejected',
            'cancellation': False,
            'errors': [
                '[1244] El campo FechaHoraHusoGenRegistro tiene un formato incorrecto.',
            ],
        }
        expected_response_info = {
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
        self.assertRecordValues(invoice, [expected_record_values])

    def test_batch_single_registered_with_errors_registration(self):
        invoice = self._create_dummy_invoice(name='INV/2019/00007', invoice_date='2024-12-17')
        document = invoice._l10n_es_edi_verifactu_create_document()
        with self._mock_zeep_registration_operation('l10n_es_edi_verifactu/tests/responses/batch_single_registered_with_errors_registration.json'):
            _batch_xml, info = document._send_as_batch()

        record_info = {
            'state': 'registered_with_errors',
            'cancellation': False,
            'errors': [
                '[2005] El campo ImporteTotal tiene un valor incorrecto para el valor de los campos BaseImponibleOimporteNoSujeto, CuotaRepercutida y CuotaRecargoEquivalencia suministrados.',
            ],
        }
        expected_response_info = {
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
        self.assertRecordValues(invoice, [expected_record_values])

    def test_response_parsing_error_document_not_found(self):
        invoice = self._create_dummy_invoice(name='INV/2019/00500', invoice_date='2024-12-17')
        document = invoice._l10n_es_edi_verifactu_create_document()
        with self._mock_zeep_registration_operation('l10n_es_edi_verifactu/tests/responses/batch_single_registered_with_errors_registration.json'):
            _batch_xml, info = document._send_as_batch()

        record_info = {
            'state': 'registered_with_errors',
            'cancellation': False,
            'errors': [
                '[2005] El campo ImporteTotal tiene un valor incorrecto para el valor de los campos BaseImponibleOimporteNoSujeto, CuotaRepercutida y CuotaRecargoEquivalencia suministrados.',
            ],
        }
        expected_response_info = {
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
        self.assertRecordValues(invoice, [expected_record_values])

    def test_mark_for_next_batch(self):
        # Check that we can send immediately
        self.assertFalse(self.company.l10n_es_edi_verifactu_next_batch_time)
        mock_accept = self._mock_zeep_registration_operation('l10n_es_edi_verifactu/tests/responses/batch_single_accepted_registration.json')

        invoice = self._create_dummy_invoice(name='INV/2019/00026', invoice_date='2024-12-30')
        with mock_accept:
            created_documents = invoice._l10n_es_edi_verifactu_mark_for_next_batch()
        document = created_documents[invoice]

        expected_document_values = {
            'document_type': 'submission',
            'state': 'accepted',
            'errors': False,
            'response_csv': 'A-YDSW8NLFLANWPM',
        }
        self.assertRecordValues(document, [expected_document_values])

        expected_record_values = {
            'l10n_es_edi_verifactu_state': 'accepted',
            'l10n_es_edi_verifactu_errors': '',
            'l10n_es_edi_verifactu_error_level': False,
        }
        self.assertRecordValues(invoice, [expected_record_values])

        # The last response indicated a waiting time of 60 seconds.
        # So the next batch should only be sent at self.fakenow + 60s
        self.assertEqual(self.company.l10n_es_edi_verifactu_next_batch_time,
                         datetime.datetime(2024, 12, 5, 0, 1, 0))

        # Try to send another invoice. Now we should not be able to send immediately.
        # Check that the cron will later be called again at the right time
        # (by checking that the trigger function was called with the right time).

        invoice = self._create_dummy_invoice(name='INV/2019/00027', invoice_date='2024-12-30')
        cron_trigger_result_dict = {}
        with mock_accept, self._mock_cron_trigger(cron_trigger_result_dict):
            created_documents = invoice._l10n_es_edi_verifactu_mark_for_next_batch()
        document = created_documents[invoice]
        self.assertEqual(cron_trigger_result_dict['at'], datetime.datetime(2024, 12, 5, 0, 1, 0))

        expected_document_values = {
            'document_type': 'submission',
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
        cron_trigger_result_dict = {}
        with self._mock_zeep_registration_operation_certificate_issue(), self._mock_cron_trigger(cron_trigger_result_dict):
            created_documents = invoice._l10n_es_edi_verifactu_mark_for_next_batch()
        document = created_documents[invoice]

        # We failed to send the document and there was no waiting time in the response since we got an access denied error
        self.assertFalse(document.state)
        self.assertFalse(self.company.l10n_es_edi_verifactu_next_batch_time)
        # So the cron has to be retriggered
        self.assertEqual(cron_trigger_result_dict['at'], datetime.datetime(2024, 12, 5, 0, 1, 0))
