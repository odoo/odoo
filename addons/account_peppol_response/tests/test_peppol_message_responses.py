import json

from odoo.tests.common import tagged, freeze_time

from odoo.addons.account_peppol.tests.test_peppol_messages import TestPeppolMessage
from odoo.addons.account_peppol.tests.common import (
    mock_ack,
    mock_documents_retrieval,
    mock_send_response,
)


@freeze_time('2023-01-01')
@tagged('-at_install', 'post_install')
class TestPeppolMessageResponse(TestPeppolMessage):

    def test_accept_response_peppol(self):
        """ Tests a basic flow of receiving a bill and accept it with the Business Level Response """
        with mock_documents_retrieval([{'uuid': self.MESSAGE_UUID, 'direction': 'incoming'}]), mock_ack():
            self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()

        move = self.env['account.move'].search([('peppol_message_uuid', '=', self.MESSAGE_UUID)])
        self.assertRecordValues(
            move, [{
                'peppol_move_state': 'done',
                'move_type': 'in_invoice',
                'state': 'draft',
            }],
        )

        self.assertRecordValues(
            move.peppol_response_ids, [{
                'peppol_state': 'processing',
                'response_code': 'AB',
            }],
        )
        with mock_documents_retrieval([{'uuid': move.peppol_response_ids.peppol_message_uuid, 'document_type': 'ApplicationResponse'}]), mock_ack():
            self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_response_ids.peppol_state, 'done')
        self.assertEqual(move.peppol_move_state, 'AB')

        move.currency_id.active = True
        # Posting the bill should send an approval response
        with mock_send_response():
            move.action_post()
        peppol_accept_response = move.peppol_response_ids.filtered(lambda r: r.response_code == 'AP')
        self.assertRecordValues(
            peppol_accept_response, [{
                'peppol_state': 'processing',
                'response_code': 'AP',
            }],
        )
        with mock_documents_retrieval([{'uuid': peppol_accept_response.peppol_message_uuid, 'document_type': 'ApplicationResponse'}]), mock_ack():
            self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'AP')

    def test_reject_response_peppol(self):
        """ Tests a basic flow of receiving a bill and accept it with the Business Level Response """
        with mock_documents_retrieval([{'uuid': self.MESSAGE_UUID, 'direction': 'incoming'}]), mock_ack():
            self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()

        move = self.env['account.move'].search([('peppol_message_uuid', '=', self.MESSAGE_UUID)])
        self.assertRecordValues(
            move, [{
                'peppol_move_state': 'done',
                'move_type': 'in_invoice',
                'state': 'draft',
            }],
        )

        self.assertRecordValues(
            move.peppol_response_ids, [{
                'peppol_state': 'processing',
                'response_code': 'AB',
            }],
        )
        with mock_documents_retrieval([{'uuid': move.peppol_response_ids.peppol_message_uuid, 'document_type': 'ApplicationResponse'}]), mock_ack():
            self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'AB')

        # Canceling the bill should return an action to open the rejection wizard
        res = move.button_cancel()
        self.assertEqual(res['res_model'], 'account.peppol.rejection.wizard')

        rejection_wizard = self.env[res['res_model']].browse(res['res_id'])
        with mock_send_response():
            rejection_wizard.button_send()
        peppol_reject_response = move.peppol_response_ids.filtered(lambda r: r.response_code == 'RE')
        self.assertRecordValues(
            peppol_reject_response, [{
                'peppol_state': 'processing',
                'response_code': 'RE',
            }],
        )
        with mock_documents_retrieval([{'uuid': peppol_reject_response.peppol_message_uuid, 'document_type': 'ApplicationResponse'}]), mock_ack():
            self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'RE')

    def test_receive_response_to_inexisting_invoices(self):
        """ Tests the case where we receive responses to invoices that we don't have in DB.
            This can happen if a user send invoices from somewhere else than its receiver endpoint.
            We should just ack it, but not bind it to a wrong invoice.
        """
        self.create_move(self.valid_partner)
        imported_move_vals = {'uuid': self.MESSAGE_UUID, 'direction': 'incoming'}
        ap_response_vals = {
            'uuid': '22222222-2222-4222-8222-222222222222',
            'filename': 'response_document',
            'state': 'done',
            'direction': 'incoming',
            'document_type': 'ApplicationResponse',
            'origin_message_uuid': 'move_uuid_that_does_not_exist_on_user_db',
        }
        with mock_documents_retrieval([imported_move_vals, ap_response_vals]):
            with mock_ack() as mocked_ack:
                self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()
                mocked_ack.assert_called_once()
                mocked_body = json.loads(mocked_ack.calls[0].body)
                self.assertEqual(len(mocked_body.get('params', {}).get('message_uuids', [])), 2)

        # Even with an existing move and an imported move, the only response expected to exist at this point is the AB response
        # sent automatically at reception of the imported move.
        imported_move = self.env['account.move'].search([('peppol_message_uuid', '!=', False)])
        self.assertEqual(len(imported_move.peppol_response_ids), 1)
        self.assertEqual(imported_move.peppol_response_ids.response_code, 'AB')

        all_peppol_responses = self.env['account.peppol.response'].search([])
        self.assertEqual(len(all_peppol_responses), 1)
