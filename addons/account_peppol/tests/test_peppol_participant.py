import json
from contextlib import contextmanager
from requests import Session, PreparedRequest, Response
from psycopg2 import IntegrityError
from unittest.mock import patch

from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import tagged, TransactionCase, freeze_time
from odoo.tools import mute_logger

ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
FAKE_UUID = 'yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy'
PDF_FILE_PATH = 'account_peppol/tests/assets/peppol_identification_test.pdf'

@freeze_time('2023-01-01')
@tagged('-at_install', 'post_install')
class TestPeppolParticipant(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('account_peppol.edi.mode', 'test')

    @classmethod
    def _get_mock_responses(cls):
        participant_state = cls.env.context.get('participant_state', 'receiver')
        return {
            '/api/peppol/2/participant_status': {
                'result': {
                    'peppol_state': participant_state,
                }
            },
            '/iap/account_edi/2/create_user': {
                'result': {
                    'id_client': ID_CLIENT,
                    'refresh_token': FAKE_UUID,
                }
            },
            '/api/peppol/1/update_user': {'result': {}},
            '/api/peppol/1/migrate_peppol_registration': {
                'result': {
                    'migration_key': 'test_key',
                }
            },
            '/api/peppol/1/register_sender': {'result': {}},
            '/api/peppol/1/register_receiver': {'result': {}},
            '/api/peppol/1/register_sender_as_receiver': {'result': {}},
            '/api/peppol/1/cancel_peppol_registration': {'result': {}},
            '/api/peppol/2/get_services': {'result': {'services': cls.env['res.company']._peppol_supported_document_types()}},
        }

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        response = Response()
        response.status_code = 200
        if r.url.endswith('/iso6523-actorid-upis%3A%3A9925%3A0000000000'):
            # 9925:0000000000 is not on Peppol
            response.status_code = 404
            return response

        if r.url.endswith('/iso6523-actorid-upis%3A%3A0208%3A0000000000'):
            # 0208:0000000000 is on Peppol
            response._content = b'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<smp:ServiceGroup xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:id="http://busdox.org/transport/identifiers/1.0/" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:smp="http://busdox.org/serviceMetadata/publishing/1.0/"><id:ParticipantIdentifier scheme="iso6523-actorid-upis">0208:0000000000</id:ParticipantIdentifier></smp:ServiceGroup>'
            return response

        url = r.path_url
        body = json.loads(r.body)
        responses = cls._get_mock_responses()
        if (
            url == '/api/peppol/2/register_participant'
            and cls.env.context.get('migrate_to')
            and not body['params'].get('migration_key')
        ):
            raise UserError('No migration key was provided')

        if cls.env.context.get('migrated_away'):
            response.json = lambda: {
                'result': {
                    'proxy_error': {
                        'code': 'no_such_user',
                        'message': 'The user does not exist on the proxy',
                    }
                }
            }
            return response

        if url not in responses:
            return super()._request_handler(s, r, **kw)
        response.json = lambda: responses[url]
        return response

    def _get_participant_vals(self):
        return {
            'peppol_eas': '9925',
            'peppol_endpoint': '0000000000',
            'phone_number': '+32483123456',
            'contact_email': 'yourcompany@test.example.com',
        }

    @contextmanager
    def _set_context(self, other_context):
        cls = self.__class__
        env = cls.env(context=dict(cls.env.context, **other_context))
        with patch.object(cls, "env", env):
            yield

    def test_create_participant_missing_data(self):
        # creating a participant without eas/endpoint/document should not be possible
        wizard = self.env['peppol.registration'].create({
            'peppol_eas': False,
            'peppol_endpoint': False,
        })
        with self.assertRaises(ValidationError), self.cr.savepoint():
            wizard.button_register_peppol_participant()

    def test_create_success_sender(self):
        company = self.env.company
        vals = self._get_participant_vals()
        vals['peppol_eas'] = '0208'
        wizard = self.env['peppol.registration'].create(vals)
        self.assertFalse(wizard.smp_registration)
        wizard.button_register_peppol_participant()
        self.assertEqual(company.account_peppol_proxy_state, 'sender')
        # running the cron should not do anything for the company
        with self._set_context({'participant_state': 'sender'}):
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
        self.assertEqual(company.account_peppol_proxy_state, 'sender')

    def test_create_success_receiver(self):
        company = self.env.company
        wizard = self.env['peppol.registration'].create(self._get_participant_vals())
        self.assertTrue(wizard.smp_registration)
        wizard.button_register_peppol_participant()
        self.assertIn(company.account_peppol_proxy_state, ('smp_registration', 'receiver'))

    def test_create_success_receiver_two_steps(self):
        company = self.env.company

        def _get_company_info_on_peppol(self, edi_identification):
            return {'is_on_peppol': True, 'external_provider': None, 'error_msg': ''}

        with patch('odoo.addons.account_peppol.models.res_company.ResCompany._get_company_info_on_peppol',
                   _get_company_info_on_peppol):
            wizard = self.env['peppol.registration'].create(self._get_participant_vals())
            wizard.button_register_peppol_participant()
        self.assertEqual(company.account_peppol_proxy_state, 'sender')
        settings = self.env['res.config.settings'].create({})
        settings.button_peppol_register_sender_as_receiver()
        self.assertIn(company.account_peppol_proxy_state, ('smp_registration', 'receiver'))
        self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
        self.assertEqual(company.account_peppol_proxy_state, 'receiver')

    def test_create_reject_participant(self):
        # the account_peppol_proxy_state should change to rejected
        # if we reject the participant
        company = self.env.company
        wizard = self.env['peppol.registration'].create(self._get_participant_vals())
        with self._set_context({'participant_state': 'rejected'}):
            wizard = wizard.with_env(self.env)
            wizard.button_register_peppol_participant()
            company.account_peppol_proxy_state = 'smp_registration'
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(company.account_peppol_proxy_state, 'rejected')

    @mute_logger('odoo.sql_db')
    def test_create_duplicate_participant(self):
        # should not be possible to create a duplicate participant
        wizard = self.env['peppol.registration'].create(self._get_participant_vals())
        wizard.button_register_peppol_participant()
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            wizard.account_peppol_proxy_state = 'not_registered'
            wizard.button_register_peppol_participant()

    def test_config_unregister_participant(self):
        wizard = self.env['peppol.registration'].create({**self._get_participant_vals(), 'peppol_eas': '0208'})
        wizard.button_register_peppol_participant()
        config_wizard = self.env['peppol.config.wizard'].new({})
        config_wizard.button_peppol_unregister()
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'not_registered')

    def test_config_update_email(self):
        wizard = self.env['peppol.registration'].create({**self._get_participant_vals(), 'peppol_eas': '0208'})
        wizard.button_register_peppol_participant()
        self.assertEqual(self.env.company.account_peppol_contact_email, self._get_participant_vals()['contact_email'])
        config_wizard = self.env['peppol.config.wizard'].new({})
        config_wizard.account_peppol_contact_email = 'another@email.be'
        with patch('odoo.addons.account_peppol.models.account_edi_proxy_user.Account_Edi_Proxy_ClientUser._call_peppol_proxy') as mocked_patch:
            config_wizard.button_sync_form_with_peppol_proxy()
            args = {'endpoint': '/api/peppol/1/update_user', 'params': {'update_data': {'peppol_contact_email': 'another@email.be'}}}
            mocked_patch.assert_called_once_with(**args)
