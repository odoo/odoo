from contextlib import contextmanager
from requests import PreparedRequest, Response, Session

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .common import ID_CLIENT, FAKE_UUID, TestL10nFrPdpCommon


@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestPdpUser(TestL10nFrPdpCommon):

    @classmethod
    def _get_mock_responses(cls):
        participant_state = cls.env.context.get('participant_state', 'receiver')
        return {
            '/api/pdp/1/connect': {
                'result': {
                    'id_client': ID_CLIENT,
                    'refresh_token': FAKE_UUID,
                }
            },
            '/api/pdp/1/register_receiver': {'result': {}},
            '/api/pdp/1/update_user': {'result': {}},
            '/api/pdp/2/participant_status': {
                'result': {
                    'peppol_state': participant_state,
                }
            },
            '/api/pdp/1/cancel_peppol_registration': {'result': {}},
        }

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        response = Response()
        response.status_code = 200

        url = r.path_url
        responses = cls._get_mock_responses()

        if url not in responses:
            return super()._request_handler(s, r, **kw)
        response.json = lambda: responses[url]
        return response

    def _get_participant_vals(self):
        return {
            'pdp_identifier': '000000000',
            'contact_email': 'yourcompany@test.example.com',
        }

    @contextmanager
    def _set_context(self, other_context):
        previous_context = self.env.context
        self.env.context = dict(previous_context, **other_context)
        try:
            yield self
        finally:
            self.env.context = previous_context

    def test_pdp_create_participant_missing_data(self):
        # creating a participant without identifier should not be possible
        wizard = self.env['pdp.registration'].create({
            'pdp_identifier': False,
        })
        with self.assertRaises(ValidationError), self.cr.savepoint():
            wizard.button_register_pdp_participant()

    def test_pdp_create_participant_receiver(self):
        company = self.env.company
        wizard = self.env['pdp.registration'].create(self._get_participant_vals())
        wizard.button_register_pdp_participant()
        self.assertEqual(company.account_peppol_proxy_state, 'smp_registration')

        # The participant should be automatically registered as receiver after some time
        with self._set_context({'participant_state': 'receiver'}):
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(self.env.company.account_peppol_proxy_state, 'receiver')

    def test_pdp_create_reject_participant(self):
        # the account_peppol_proxy_state should change to rejected
        # if we reject the participant
        company = self.env.company
        wizard = self.env['pdp.registration'].create(self._get_participant_vals())

        with self._set_context({'participant_state': 'rejected'}):
            wizard.button_register_pdp_participant()
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(company.account_peppol_proxy_state, 'rejected')

    def test_pdp_create_duplicate_participant(self):
        """ If you create a duplicate participant, it will take over the previous one"""
        wizard = self.env['pdp.registration'].create(self._get_participant_vals())
        wizard.button_register_pdp_participant()

        wizard.account_peppol_proxy_state = False
        wizard.button_register_pdp_participant()
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'smp_registration')

        # The participant is still a receiver on IAP
        with self._set_context({'participant_state': 'receiver'}):
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(self.env.company.account_peppol_proxy_state, 'receiver')

    def test_peppol_pdp_unqiue_constraint(self):
        """Test that we can either have a PDP or a Peppol user per company (and per edi mode)"""
        self.assertRecordValues(self.proxy_user, [{
            'active': True,
            'company_id': self.env.company.id,
            'proxy_type': 'pdp',
            'edi_mode': 'test',
        }])

        with self.assertRaises(Exception), mute_logger('odoo.sql_db'):
            self.env['account_edi_proxy_client.user'].create([{
                'active': True,
                'id_client': 'client-demo',
                'company_id': self.env.company.id,
                'edi_identification': 'client-demo',
                'private_key_id': self.env['certificate.key'].sudo()._generate_rsa_private_key(self.env.company).id,
                'refresh_token': False,
                'proxy_type': 'pdp',
                'edi_mode': 'test',
            }])

        with self.assertRaises(Exception), mute_logger('odoo.sql_db'):
            self.env['account_edi_proxy_client.user'].create([{
                'active': True,
                'id_client': 'client-demo',
                'company_id': self.env.company.id,
                'edi_identification': 'client-demo',
                'private_key_id': self.env['certificate.key'].sudo()._generate_rsa_private_key(self.env.company).id,
                'refresh_token': False,
                'proxy_type': 'peppol',
                'edi_mode': 'test',
            }])

        other_company = self.setup_other_company(name='other')['company']
        other_pdp_user = self.env['account_edi_proxy_client.user'].create([{
            'active': True,
            'id_client': 'client-demo-pdp',
            'company_id': other_company.id,
            'edi_identification': 'client-demo',
            'private_key_id': self.env['certificate.key'].sudo()._generate_rsa_private_key(self.env.company).id,
            'refresh_token': False,
            'proxy_type': 'pdp',
            'edi_mode': 'test',
        }])
        self.assertTrue(other_pdp_user)

        other2_company = self.setup_other_company(name='other2')['company']
        other2_peppol_user = self.env['account_edi_proxy_client.user'].create([{
            'active': True,
            'id_client': 'client-demo-peppol',
            'company_id': other2_company.id,
            'edi_identification': 'client-demo',
            'private_key_id': self.env['certificate.key'].sudo()._generate_rsa_private_key(self.env.company).id,
            'refresh_token': False,
            'proxy_type': 'peppol',
            'edi_mode': 'test',
        }])
        self.assertTrue(other2_peppol_user)
