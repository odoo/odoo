from unittest.mock import Mock, patch

from odoo.tests.common import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestTokenSyncResolution(TransactionCase):

    @classmethod
    @patch('requests.post')
    def setUpClass(cls, mock_post):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('account_peppol.edi.mode', 'test')

        def mock_response(url, *_args, **_kwargs):
            response = Mock()
            if url.endswith('/iap/account_edi/2/create_user'):
                response.json.return_value = {
                    'jsonrpc': '2.0',
                    'result': {
                        'id_client': 'mock-id-client',
                        'refresh_token': 'mock-refresh-token',
                    },
                }
            elif url.endswith('/api/peppol/1/participant_status'):
                response.json.return_value = {
                    'jsonrpc': '2.0',
                    'result': {'peppol_state': 'active'},
                }
            else:
                response.json.return_value = {'jsonrpc': '2.0', 'result': {}}
            response.status_code = 200
            return response

        mock_post.side_effect = mock_response

        cls.company = cls.env.company
        cls.settings = cls.env['res.config.settings'].create({
            'account_peppol_eas': '9925',
            'account_peppol_endpoint': '0000000000',
            'account_peppol_phone_number': '+32483123456',
            'account_peppol_contact_email': 'yourcompany@test.example.com',
        })

        cls.settings.button_create_peppol_proxy_user()
        cls.settings.button_send_peppol_verification_code()
        cls.settings.account_peppol_verification_code = '123456'
        cls.settings.button_check_peppol_verification_code()
        cls.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()

    @patch('requests.post')
    def test_peppol_out_of_sync_detection(self, mock_post):
        mock_post.side_effect = [
            Mock(status_code=200, json=Mock(return_value={
                'result': {'proxy_error': {'code': 'invalid_signature', 'message': 'Invalid signature'}}
            })),
            Mock(status_code=200, json=Mock(return_value={'result': {}})),
        ]

        user = self.env['account_edi_proxy_client.user'].search([
            ('company_id', '=', self.company.id),
            ('proxy_type', '=', 'peppol'),
        ], limit=1)

        self.assertFalse(user.peppol_token_out_of_sync)

        with self.assertLogs('odoo.addons.account_peppol.models.account_edi_proxy_user') as log_catcher:
            user._peppol_get_participant_status()

        self.assertTrue(user.peppol_token_out_of_sync)
        self.assertEqual(mock_post.call_count, 2)
        self.assertIn(
            "please go to Settings > Accounting > Peppol Settings and click on 'Reconnect this database'",
            log_catcher.output[0]
        )
