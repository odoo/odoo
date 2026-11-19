import base64
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_gr_edi_delivery_note.tests.common import TestMyDATADeliveryNoteCommon
from odoo.addons.l10n_gr_edi_e_invoo_bridge.exceptions import EInvooAuthenticationError, EInvooRequestError
from odoo.addons.l10n_gr_edi_e_invoo_bridge.models.account_move import E_INVOO_TOKEN_NOT_SET

BRIDGE = 'odoo.addons.l10n_gr_edi_e_invoo_bridge.models.account_move.AccountMove'


def _issued_result(**overrides):
    """Response of e-invoo for an issued delivery note, as returned by the test environment."""
    response = {
        'success': True,
        'b1_auth_string': 'AUTHENTICATION-CODE',
        'provider_uid': 'PROVIDER-UID',
        'mark': 400001976153455,  # e-invoo returns an int on the first submission
        'uid': 'MYDATA-UID',
        'qrUrl': 'https://mydataapidev.aade.gr/TimologioQR/QRInfo?q=abc',
        'inv_identifier': 'DOCUMENT-IDENTIFIER',
        'provider_qrUrl': 'https://test.e-invoo.com/verify/642/PARENT-TOKEN',
    }
    response.update(overrides)
    return {'upstream_status': 200, 'response': response}


def _pdf_result(found=True):
    return {'upstream_status': 200, 'response': {'Found': found, 'record': 642 if found else None}}


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestMyDATADeliveryNoteEInvoo(TestMyDATADeliveryNoteCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_gr_edi_methodoos_api_token = 'token'

    def _get_document(self, picking):
        return picking.l10n_gr_edi_document_ids.sorted()[:1]

    @patch(f'{BRIDGE}._l10n_gr_edi_post_e_invoo', return_value=_pdf_result())
    @patch(f'{BRIDGE}._l10n_gr_edi_issue_invoice', return_value=_issued_result())
    def test_issue_delivery_note_and_upload_pdf(self, mock_issue, mock_post):
        picking = self._create_picking()
        self.assertTrue(picking.l10n_gr_edi_enable_send)

        picking.action_l10n_gr_edi_try_send_delivery_note()

        mock_issue.assert_called_once()
        request_values = mock_issue.call_args.kwargs['request_values']
        self.assertEqual(mock_issue.call_args.args[0], 'token')
        self.assertEqual(request_values['invoice_id'], str(picking.id))
        self.assertEqual(request_values['invoice_name'], picking.name)
        self.assertEqual(request_values['invoice_amount_total'], 0)
        self.assertNotIn('invoice_currency', request_values)
        self.assertIn('<invoiceType>9.3</invoiceType>', request_values['xml'])

        document = self._get_document(picking)
        self.assertRecordValues(document, [{
            'state': 'delivery_note_sent',
            'mydata_mark': '400001976153455',
            'mydata_uid': 'MYDATA-UID',
            'mydata_authentication_code': 'AUTHENTICATION-CODE',
            'provider_invoice_identifier': 'DOCUMENT-IDENTIFIER',
            'provider_qr_url': 'https://test.e-invoo.com/verify/642/PARENT-TOKEN',
            'provider_pdf_state': 'sent',
            'message': False,
        }])
        self.assertRecordValues(picking, [{
            'l10n_gr_edi_state': 'delivery_note_sent',
            'l10n_gr_edi_mark': '400001976153455',
            'l10n_gr_edi_enable_send': False,
        }])

        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.kwargs['endpoint'], 'save_invoice_fpdf')
        pdf_values = mock_post.call_args.kwargs['json']
        self.assertEqual(pdf_values['invoice_id'], request_values['invoice_id'])
        self.assertEqual(pdf_values['parent_token'], 'PARENT-TOKEN')
        self.assertTrue(base64.b64decode(pdf_values['pdf_b64']))

        report_values = picking._l10n_gr_edi_get_extra_invoice_report_values()
        self.assertEqual(report_values['verification_url'], document.provider_qr_url)
        self.assertEqual(report_values['provider_invoice_identifier'], 'DOCUMENT-IDENTIFIER')
        self.assertIn('provider_software_license', report_values)

    @patch(f'{BRIDGE}._l10n_gr_edi_post_e_invoo', return_value=_pdf_result())
    @patch(f'{BRIDGE}._l10n_gr_edi_issue_invoice')
    def test_unknown_result_reuses_pending_submission(self, mock_issue, mock_post):
        picking = self._create_picking()

        mock_issue.side_effect = EInvooRequestError()
        picking.action_l10n_gr_edi_try_send_delivery_note()
        pending_document = self._get_document(picking)
        self.assertEqual(pending_document.state, 'delivery_note_pending')
        self.assertEqual(picking.l10n_gr_edi_state, 'delivery_note_pending')
        self.assertTrue(pending_document.message)
        first_request = mock_issue.call_args.kwargs['request_values']

        # The data changes after the first submission, but the retry must send the exact same request.
        # e-invoo then returns the already issued document, without its identifier.
        picking.l10n_gr_edi_vehicle_number = 'XYZ9999'
        mock_issue.side_effect = None
        mock_issue.return_value = _issued_result(mark='400001976153455', inv_identifier=None)
        picking.action_l10n_gr_edi_try_send_delivery_note()

        self.assertEqual(mock_issue.call_args.kwargs['request_values'], first_request)
        self.assertEqual(self._get_document(picking), pending_document)
        self.assertRecordValues(pending_document, [{
            'state': 'delivery_note_sent',
            'mydata_mark': '400001976153455',
            'provider_invoice_identifier': False,
            'provider_pdf_state': 'sent',
        }])
        self.assertEqual(picking.l10n_gr_edi_state, 'delivery_note_sent')

    @patch(f'{BRIDGE}._l10n_gr_edi_post_e_invoo', return_value=_pdf_result())
    @patch(f'{BRIDGE}._l10n_gr_edi_issue_invoice')
    def test_errors_start_a_fresh_submission(self, mock_issue, mock_post):
        picking = self._create_picking()

        mock_issue.return_value = {'upstream_status': 200, 'response': {'success': False, 'error': 'tf2'}}
        picking.action_l10n_gr_edi_try_send_delivery_note()
        failed_document = self._get_document(picking)
        self.assertEqual(failed_document.state, 'delivery_note_error')
        self.assertIn('TF2', failed_document.message)
        self.assertEqual(picking.l10n_gr_edi_state, 'delivery_note_error')

        mock_issue.return_value = {
            'upstream_status': 200,
            'response': {'success': False, 'error': 'Counterpart Name is mandatory for this invoice type '},
        }
        picking.action_l10n_gr_edi_try_send_delivery_note()
        rejected_document = self._get_document(picking)
        self.assertNotEqual(rejected_document, failed_document)
        self.assertRecordValues(rejected_document, [{
            'state': 'delivery_note_error',
            'message': 'Counterpart Name is mandatory for this invoice type ',
        }])

        mock_issue.side_effect = EInvooAuthenticationError
        picking.action_l10n_gr_edi_try_send_delivery_note()
        unauthorized_document = self._get_document(picking)
        self.assertNotIn(unauthorized_document, rejected_document | failed_document)
        self.assertRecordValues(unauthorized_document, [{
            'state': 'delivery_note_error',
            'message': str(EInvooAuthenticationError()),
        }])

        mock_issue.side_effect = None
        mock_issue.return_value = _issued_result()
        picking.action_l10n_gr_edi_try_send_delivery_note()
        self.assertEqual(picking.l10n_gr_edi_state, 'delivery_note_sent')
        # The failed attempts are cleaned once the delivery note is issued
        self.assertEqual(picking.l10n_gr_edi_document_ids.mapped('state'), ['delivery_note_sent'])

    @patch(f'{BRIDGE}._l10n_gr_edi_post_e_invoo')
    @patch(f'{BRIDGE}._l10n_gr_edi_issue_invoice', return_value=_issued_result())
    def test_pdf_failures_keep_the_issued_delivery_note(self, mock_issue, mock_post):
        picking = self._create_picking()

        def pdf_attachments():
            return picking.message_ids.attachment_ids.filtered(lambda attachment: attachment.mimetype == 'application/pdf')

        # The final PDF cannot be rendered
        with patch(
            'odoo.addons.base.models.ir_actions_report.IrActionsReport._render_qweb_pdf',
            side_effect=UserError("Wkhtmltopdf failed"),
        ):
            picking.action_l10n_gr_edi_try_send_delivery_note()
        document = self._get_document(picking)
        self.assertRecordValues(document, [{
            'state': 'delivery_note_sent',
            'provider_pdf_state': 'error',
            'provider_pdf_error': "Wkhtmltopdf failed",
        }])
        mock_post.assert_not_called()
        self.assertTrue(picking.l10n_gr_edi_enable_send)

        # e-invoo answers 200 with `Found: false` when it cannot match the document
        mock_post.return_value = _pdf_result(found=False)
        picking.action_l10n_gr_edi_try_send_delivery_note()
        self.assertEqual(document.provider_pdf_state, 'error')
        self.assertTrue(picking.l10n_gr_edi_enable_send)
        self.assertFalse(pdf_attachments())

        # Retrying only uploads the PDF again: the delivery note is not issued twice
        mock_post.return_value = _pdf_result()
        picking.action_l10n_gr_edi_try_send_delivery_note()
        mock_issue.assert_called_once()
        self.assertEqual(document.provider_pdf_state, 'sent')
        self.assertFalse(picking.l10n_gr_edi_enable_send)
        self.assertTrue(pdf_attachments())

    @patch(f'{BRIDGE}._l10n_gr_edi_issue_invoice')
    def test_missing_token(self, mock_issue):
        self.env.company.l10n_gr_edi_methodoos_api_token = False
        picking = self._create_picking()
        self.assertIn('l10n_gr_edi_missing_methodoos_token', picking._l10n_gr_edi_get_pre_error_dict())
        with self.assertRaisesRegex(UserError, str(E_INVOO_TOKEN_NOT_SET)):
            picking.action_l10n_gr_edi_try_send_delivery_note()
        mock_issue.assert_not_called()
        self.assertFalse(picking.l10n_gr_edi_document_ids)
