from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError


@tagged('-at_install', 'post_install')
class TestTokenSyncResolution(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('account_peppol.edi.mode', 'test')

        cls.env.company.write({'peppol_eas': '0208', 'peppol_endpoint': '0239843188'})
        edi_identification = cls.env['account_edi_proxy_client.user']._get_proxy_identification(
            cls.env.company, 'peppol'
        )
        private_key = cls.env['certificate.key'].sudo()._generate_rsa_private_key(cls.env.company)
        cls.user = cls.env['account_edi_proxy_client.user'].create({
            'company_id': cls.env.company.id,
            'id_client': 'mock-id-client',
            'proxy_type': 'peppol',
            'edi_mode': 'test',
            'edi_identification': edi_identification,
            'private_key_id': private_key.id,
            'refresh_token': 'mock-refresh-token',
        })

    def test_peppol_out_of_sync_detection(self):
        def fake_call(endpoint, params=None, auth_type=None):
            if endpoint.endswith('/api/peppol/2/participant_status'):
                raise AccountEdiProxyError('invalid_signature')
            return {}

        self.assertFalse(self.user.is_token_out_of_sync)

        with patch(
            'odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user.Account_Edi_Proxy_ClientUser._make_request',
            side_effect=fake_call
        ), self.assertRaises(UserError) as e:
            self.user._peppol_get_participant_status()

        self.assertIn("please go to Settings > Accounting > Peppol Settings and click on 'Reconnect this database'", e.exception.args[0])
