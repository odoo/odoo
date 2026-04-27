from unittest.mock import patch
import requests

from markupsafe import Markup

from .common import TestL10nCoEdiPosCommon

from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDianPos(TestL10nCoEdiPosCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.default_pos_order_ui_data = {
            'pos_order_lines_ui_args': [(cls.product_a, 2)],
            'payments': [(cls.default_pos_payment_method, 2380.0)]
        }

    def _mock_get_status_zip_pos_order(self, order, response_file, response_code=200):
        with patch.object(requests, 'post', return_value=self._mocked_request(response_file, response_code)):
            order.l10n_co_edi_pos_document_ids._get_status_zip()

    def _send_test_set_async(self):
        self.config.company_id.write({
            'l10n_co_dian_test_environment': True,
            'l10n_co_dian_certification_process': True,
        })

        order = self._create_and_send_order(pos_order_ui_data=self.default_pos_order_ui_data, response_file_name='SendTestSetAsync.xml')
        self.assertRecordValues(order.l10n_co_edi_pos_document_ids, [{
            'zip_key': '42424242',
            'state': 'invoice_pending',
            'message': Markup("<p>Invoice is being processed by the DIAN.</p>"),
        }])
        self.assertEqual(order.l10n_co_edi_pos_dian_state, 'invoice_pending')
        return order

    def test_get_status_zip_warnings(self):
        """ SendTestSetAsync then GetStatusZip which returns warnings but the document is valid. """
        # Step 1: SendTestSetAsync
        order = self._send_test_set_async()
        # Step 2: GetStatusZip
        self._mock_get_status_zip_pos_order(order=order, response_file='GetStatusZip_warnings.xml')

        # checks on the document
        self.assertEqual(len(order.l10n_co_edi_pos_document_ids), 1)
        self.assertRecordValues(order.l10n_co_edi_pos_document_ids, [{
            'zip_key': '42424242',
            'state': 'invoice_accepted',
            'message': Markup(
                "<p>Procesado Correctamente.</p>"
                "<ul><li>Regla: FAJ44b, Notificación: Nit o Documento de Identificación BlaBlaBla.</li>"
                "<li>Regla: FAJ43b, Notificación: Nombre informado No corresponde al BlaBlaBla.</li></ul>"
            ),
        }])
        # checks on the invoice
        self.assertTrue(order.l10n_co_edi_pos_attachment_id)
        self.assertEqual(order.l10n_co_edi_pos_dian_state, 'invoice_accepted')

    def test_get_status_zip_habilitation(self):
        """ SendTestSetAsync then GetStatusZip which inform that they passed the habitation process. """
        # Step 1: SendTestSetAsync
        order = self._send_test_set_async()
        # Step 2: GetStatusZip
        self._mock_get_status_zip_pos_order(order, response_file='GetStatusZip_habilitation.xml')

        # checks on the document
        self.assertEqual(len(order.l10n_co_edi_pos_document_ids), 1)
        self.assertRecordValues(order.l10n_co_edi_pos_document_ids, [{
            'zip_key': '42424242',
            'state': 'invoice_rejected',
            'message': Markup("<p>Set de prueba con identificador 123456 se encuentra Aceptado.</p>"),
        }])
        # checks on the invoice
        self.assertFalse(order.l10n_co_edi_pos_attachment_id)
        self.assertEqual(order.l10n_co_edi_pos_dian_state, 'invoice_rejected')

    def test_get_status_zip_pending(self):
        """ SendTestSetAsync then GetStatusZip which responds 'Batch is being processed' (need to check again later)"""
        # Step 1: SendTestSetAsync
        order = self._send_test_set_async()
        # Step 2: GetStatusZip
        self._mock_get_status_zip_pos_order(order, response_file='GetStatusZip_pending.xml')

        # checks on the document
        self.assertEqual(len(order.l10n_co_edi_pos_document_ids), 1)
        self.assertRecordValues(order.l10n_co_edi_pos_document_ids, [{
            'zip_key': '42424242',
            'state': 'invoice_pending',
            'message': Markup("<p>Batch en proceso de validación.</p>"),
            'show_button_get_status': True,
        }])
        # checks on the invoice
        self.assertFalse(order.l10n_co_edi_pos_attachment_id)
        self.assertEqual(order.l10n_co_edi_pos_dian_state, 'invoice_pending')

        # Step 3: GetStatusZip again (this time the document is processed)
        self._mock_get_status_zip_pos_order(order, response_file='GetStatusZip_warnings.xml')

        # checks on the document
        self.assertEqual(len(order.l10n_co_edi_pos_document_ids), 1)
        self.assertRecordValues(order.l10n_co_edi_pos_document_ids, [{
            'zip_key': '42424242',
            'state': 'invoice_accepted',
            'message': Markup(
                "<p>Procesado Correctamente.</p>"
                "<ul><li>Regla: FAJ44b, Notificación: Nit o Documento de Identificación BlaBlaBla.</li>"
                "<li>Regla: FAJ43b, Notificación: Nombre informado No corresponde al BlaBlaBla.</li></ul>"
            ),
        }])
        # checks on the invoice
        self.assertTrue(order.l10n_co_edi_pos_attachment_id)
        self.assertEqual(order.l10n_co_edi_pos_dian_state, 'invoice_accepted')

    def test_send_bill_sync_warnings(self):
        """ SendBillSync returning warnings but the document is valid. """
        order = self._create_and_send_order(pos_order_ui_data=self.default_pos_order_ui_data, response_file_name='SendBillSync_warnings.xml')
        self.assertTrue(order.l10n_co_edi_pos_attachment_id)
        self.assertRecordValues(order.l10n_co_edi_pos_document_ids, [{
            'zip_key': False,
            'state': 'invoice_accepted',
            'message': Markup(
                "<p>Procesado Correctamente.</p>"
                "<ul><li>Regla: FAJ44b, Notificación: Nit o Documento de Identificación informado No BlaBlaBla.</li>"
                "<li>Regla: FAJ43b, Notificación: Nombre informado No corresponde al registrado en el BlaBlaBla.</li></ul>"
            ),
        }])

    def test_send_bill_sync_errors(self):
        """ SendBillSync returning errors blocking the Send & Print flow. """
        error_raised = False
        try:
            self._create_and_send_order(pos_order_ui_data=self.default_pos_order_ui_data, response_file_name='SendBillSync_errors.xml')
        except UserError as e:
            error_raised = True
            self.assertEqual(e.args[0], "Error(s) when sending the document to the DIAN:\n"
                                        "- Regla: ZB01, Rechazo: Fallo en el esquema XML del archivo")

        self.assertTrue(error_raised)
        order = self.config.session_ids.order_ids[0]
        self.assertRecordValues(order.l10n_co_edi_pos_document_ids, [{
            'zip_key': False,
            'state': 'invoice_rejected',
            'message': Markup(
                "<p>Documento con errores en campos mandatorios.</p>"
                "<ul><li>Regla: ZB01, Rechazo: Fallo en el esquema XML del archivo</li></ul>"
            ),
        }])

        return order

    def test_send_bill_sync_errors_nsmap(self):
        """ SendBillSync returning errors due to a missing namespace, blocking the Send & Print flow. """
        error_raised = False
        try:
            self._create_and_send_order(pos_order_ui_data=self.default_pos_order_ui_data, response_file_name='SendBillSync_errors_nsmap.xml')
        except UserError as e:
            error_raised = True
            self.assertEqual(e.args[0], "Error(s) when sending the document to the DIAN:\n- Error al parsear xml. Namespace prefix 'sts' is not defined.")

        self.assertTrue(error_raised)
        order = self.config.session_ids.order_ids[0]
        self.assertRecordValues(order.l10n_co_edi_pos_document_ids, [{
            'zip_key': False,
            'state': 'invoice_rejected',
            'message': Markup("<p>Error al parsear xml. Namespace prefix 'sts' is not defined.</p>"),
        }])

    def test_send_bill_sync_duplicated(self):
        """ SendBillSync returning 'Regla: 90, Rechazo: Documento procesado anteriormente.'
        This means an invoice with the same CUFE has already been accepted by the DIAN.
        """
        error_raised = False
        try:
            self._create_and_send_order(pos_order_ui_data=self.default_pos_order_ui_data, response_file_name='SendBillSync_duplicated.xml')
        except UserError as e:
            error_raised = True
            self.assertEqual(e.args[0], "Error(s) when sending the document to the DIAN:\n"
                                        "- Regla: 90, Rechazo: Documento procesado anteriormente.")

        self.assertTrue(error_raised)
        order = self.config.session_ids.order_ids[0]
        self.assertRecordValues(order.l10n_co_edi_pos_document_ids, [{
            'zip_key': False,
            'state': 'invoice_rejected',
            'message': Markup(
                "<p>Validación contiene errores en campos mandatorios.</p>"
                "<ul><li>Regla: 90, Rechazo: Documento procesado anteriormente.</li></ul>"
            ),
        }])

    def test_send_bill_sync_second_attempt(self):
        """ First attempt SendBillSync returns errors, second attempt is successful. """
        # 1st attempt (fail)
        order = self.test_send_bill_sync_errors()

        self.assertFalse(order.l10n_co_edi_pos_attachment_id)
        self.assertRecordValues(order.l10n_co_edi_pos_document_ids, [{
            'zip_key': False,
            'state': 'invoice_rejected',
            'message': Markup(
                "<p>Documento con errores en campos mandatorios.</p>"
                "<ul><li>Regla: ZB01, Rechazo: Fallo en el esquema XML del archivo</li></ul>"
            ),
        }])

        # 2nd attempt (success without errors or warnings)
        with (
            self.patched_document('_parse_errors', []),
            self._mock_get_status(),
            patch(f'{self.utils_path}._build_and_send_request', return_value=self._mocked_response('SendBillSync_warnings.xml', 200)),
        ):
            order.l10n_co_edi_pos_action_send_document()

        self.assertEqual(len(order.l10n_co_edi_pos_document_ids), 1)  # no need to keep the rejected documents
        self.assertTrue(order.l10n_co_edi_pos_attachment_id)
        self.assertRecordValues(order.l10n_co_edi_pos_document_ids, [{
            'zip_key': False,
            'state': 'invoice_accepted',
            'message': Markup("<p>Procesado Correctamente.</p>"),
        }])

    def test_invoiced_pos_order(self):
        self.config.company_id.write({
            'l10n_co_dian_test_environment': True,
            'l10n_co_dian_certification_process': True,
        })

        with (
            self._pos_session(),
            self._mock_get_status(),
            self._disable_get_acquirer_call(),
            patch(f'{self.utils_path}._build_and_send_request', return_value=self._mocked_response('SendTestSetAsync.xml', 200)),
        ):
            order = self._create_order({
                **self.default_pos_order_ui_data,
                'is_invoiced': True,
                'customer': self.partner_co,
            })

            self.assertRecordValues(order, [{
                'to_invoice': True,
                'l10n_co_edi_pos_document_ids': self.env['l10n_co_dian.document'],
            }])
            self.assertTrue(order.account_move)

            move = order.account_move
            self._mock_send_and_print(move=move, response_file='SendTestSetAsync.xml')

            self.assertRecordValues(move.l10n_co_dian_document_ids, [{
                'zip_key': '42424242',
                'state': 'invoice_pending',
                'message': Markup("<p>Invoice is being processed by the DIAN.</p>"),
            }])
            self.assertEqual(move.l10n_co_dian_state, 'invoice_pending')

    def test_session_report(self):
        self.config.company_id.write({
            'l10n_co_dian_test_environment': True,
            'l10n_co_dian_certification_process': True,
        })
        self.config.l10n_co_edi_pos_serial_number = "Test CO SN"

        with (
            self._pos_session(),
            self._mock_get_status(),
            self._disable_get_acquirer_call(),
            patch(f'{self.utils_path}._build_and_send_request', return_value=self._mocked_response('SendTestSetAsync.xml', 200)),
        ):
            order = self._create_order({
                **self.default_pos_order_ui_data,
                'is_invoiced': True,
                'customer': self.partner_co,
            })
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(
            config_ids=order.session_id.config_id.ids,
            session_ids=order.session_id.ids
        )
        self.assertIn("Test CO SN", report['l10n_co_edi_pos_serial_number'])
