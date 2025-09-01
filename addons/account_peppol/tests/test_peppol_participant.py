import json
from base64 import b64encode
from contextlib import contextmanager
from requests import Session, PreparedRequest, Response
from psycopg2 import IntegrityError
from unittest.mock import patch

from odoo.exceptions import ValidationError, UserError, AccessError
from odoo.tests.common import tagged, TransactionCase, freeze_time
from odoo.tools import mute_logger
from odoo.tools.misc import file_open

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
        cls.private_key = cls.env['certificate.key'].create([{
            'name': 'Test key PEPPOL',
            'content': b64encode(file_open('account_peppol/tests/assets/private_key.pem', 'rb').read()),
        }])

    def _patch_register_proxy_user_id_client(self, new_id_client_character: str):
        assert len(new_id_client_character) == 1
        return patch(
            # use different ID client to avoid unique error when creating the new EDI user
            'odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user.Account_Edi_Proxy_ClientUser._register_proxy_user',
            lambda edi_user, company, proxy_type, edi_mode: edi_user.create([{
                'id_client': ID_CLIENT.replace('x', new_id_client_character),
                'company_id': company.id,
                'proxy_type': proxy_type,
                'edi_mode': edi_mode,
                'edi_identification': f'{company.peppol_eas}:{company.peppol_endpoint}',
                'private_key_id': self.private_key.id,
                'refresh_token': FAKE_UUID,
            }])
        )

    def _get_branch_companies_setup(self, register_branch_spoiled=False):
        parent_company = self.env.company
        parent_wizard = self.env['peppol.registration'].create([self._get_participant_vals()])
        parent_wizard.button_register_peppol_participant()
        branch_spoiled, branch_independent = self.env['res.company'].create([
            {
                'name': 'BE Spoiled Kid',
                'country_id': self.env.ref('base.be').id,
                'parent_id': self.env.company.id,
            },
            {
                'name': 'BE Independent Kid',
                'country_id': self.env.ref('base.be').id,
                'parent_id': self.env.company.id,
            },
        ])
        self.cr.precommit.run()  # load the COA

        if register_branch_spoiled:
            with self._patch_register_proxy_user_id_client('a'):
                self.env['peppol.registration'] \
                    .with_company(branch_spoiled) \
                    .create([{}]) \
                    .button_register_peppol_participant()
            self.assertTrue(branch_spoiled.account_peppol_edi_user)
            self.assertTrue(branch_spoiled.peppol_parent_company_id)

        return parent_company, branch_spoiled, branch_independent

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
        url = r.path_url.lower()
        if url.endswith('/iso6523-actorid-upis%3A%3A9925%3ABE0239843188'.lower()):
            # 9925:0000000000 is not on Peppol
            response.status_code = 404
            return response

        if url.endswith('/iso6523-actorid-upis%3A%3A0208%3A0239843188'.lower()):
            # 0208:0000000000 is on Peppol
            response._content = b'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<smp:ServiceGroup xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:id="http://busdox.org/transport/identifiers/1.0/" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:smp="http://busdox.org/serviceMetadata/publishing/1.0/"><id:ParticipantIdentifier scheme="iso6523-actorid-upis">0208:0239843188</id:ParticipantIdentifier></smp:ServiceGroup>'
            return response

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
            'peppol_endpoint': 'BE0239843188',
            'phone_number': '+32483123456',
            'contact_email': 'yourcompany@test.example.com',
        }

    @contextmanager
    def _set_context(self, other_context):
        cls = self.__class__
        env = cls.env(context=dict(cls.env.context, **other_context))
        with patch.object(cls, "env", env):
            yield

    def test_ignore_archived_edi_users(self):
        wizard = self.env['peppol.registration'].create(self._get_participant_vals())
        wizard.button_register_peppol_participant()

        self.env['account_edi_proxy_client.user'].create([{
            'active': False,
            'id_client': 'client-demo',
            'company_id': self.env.company.id,
            'edi_identification': 'client-demo',
            'private_key_id': self.env['certificate.key'].sudo()._generate_rsa_private_key(self.env.company).id,
            'refresh_token': False,
            'proxy_type': 'peppol',
            'edi_mode': 'demo',
        }])
        self.env.company.with_context(active_test=False).partner_id.button_account_peppol_check_partner_endpoint()

    def test_create_participant_missing_data(self):
        # creating a participant without eas/endpoint/document should not be possible
        wizard = self.env['peppol.registration'].create({
            'peppol_eas': False,
            'peppol_endpoint': False,
        })
        with self.assertRaises(ValidationError):
            wizard.button_register_peppol_participant()

    def test_create_success_sender(self):
        company = self.env.company
        vals = {**self._get_participant_vals(), 'peppol_eas': '0208', 'peppol_endpoint': '0239843188'}
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
        with self.assertRaises(IntegrityError):
            wizard.account_peppol_proxy_state = 'not_registered'
            wizard.button_register_peppol_participant()

    def test_config_unregister_participant(self):
        wizard = self.env['peppol.registration'].create({**self._get_participant_vals(), 'peppol_eas': '0208', 'peppol_endpoint': '0239843188'})
        wizard.button_register_peppol_participant()
        config_wizard = self.env['peppol.config.wizard'].new({})
        config_wizard.button_peppol_unregister()
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'not_registered')

    def test_config_update_email(self):
        wizard = self.env['peppol.registration'].create({**self._get_participant_vals(), 'peppol_eas': '0208', 'peppol_endpoint': '0239843188'})
        wizard.button_register_peppol_participant()
        self.assertEqual(self.env.company.account_peppol_contact_email, self._get_participant_vals()['contact_email'])
        config_wizard = self.env['peppol.config.wizard'].new({})
        config_wizard.account_peppol_contact_email = 'another@email.be'
        with patch('odoo.addons.account_peppol.models.account_edi_proxy_user.Account_Edi_Proxy_ClientUser._call_peppol_proxy') as mocked_patch:
            config_wizard.button_sync_form_with_peppol_proxy()
            args = {'endpoint': '/api/peppol/1/update_user', 'params': {'update_data': {'peppol_contact_email': 'another@email.be'}}}
            mocked_patch.assert_called_once_with(**args)

    def test_peppol_branch_spoiled_registration(self):
        """
        Register branch_spoiled to use parent connection
        """
        parent_company, branch_spoiled, _branch_independent = self._get_branch_companies_setup()
        wizard_spoiled = self.env['peppol.registration'].with_company(branch_spoiled).create([{}])
        self.assertRecordValues(wizard_spoiled, [{
            'active_parent_company': parent_company.id,
            'active_parent_company_name': parent_company.name,
            'is_branch_company': True,
            'selected_company_id': parent_company.id,
            'peppol_eas': parent_company.peppol_eas,
            'peppol_endpoint': parent_company.peppol_endpoint,
            'contact_email': parent_company.account_peppol_contact_email,
            'phone_number': parent_company.account_peppol_phone_number,
        }])
        with self._patch_register_proxy_user_id_client('a'):
            wizard_spoiled.button_register_peppol_participant()
        self.assertRecordValues(branch_spoiled, [{
            'peppol_parent_company_id': parent_company.id,
            'peppol_eas': parent_company.peppol_eas,
            'peppol_endpoint': parent_company.peppol_endpoint,
            'account_peppol_contact_email': parent_company.account_peppol_contact_email,
            'account_peppol_phone_number': parent_company.account_peppol_phone_number,
        }])

    def test_peppol_branch_spoiled_reconnect(self):
        """
        `branch_spoiled` should be able to disconnect/reconnect freely
        """
        _parent_company, branch_spoiled, _branch_independent = self._get_branch_companies_setup(register_branch_spoiled=True)
        settings_spoiled = self.env['res.config.settings'].with_company(branch_spoiled).create([{}])
        with (
            patch('odoo.addons.account_peppol.models.account_edi_proxy_user.Account_Edi_Proxy_ClientUser._cron_peppol_get_message_status'),
            patch('odoo.addons.account_peppol.models.account_edi_proxy_user.Account_Edi_Proxy_ClientUser._cron_peppol_get_new_documents'),
        ):  # prevent external request from the CRONs
            settings_spoiled.button_peppol_disconnect_branch_from_parent()
        self.assertFalse(branch_spoiled.peppol_parent_company_id)
        wizard_spoiled = self.env['peppol.registration'].with_company(branch_spoiled).create([{}])
        with self._patch_register_proxy_user_id_client('a'):
            wizard_spoiled.button_register_peppol_participant()
        self.assertTrue(branch_spoiled.peppol_parent_company_id)

    def test_peppol_branch_spoiled_user_access(self):
        """
        User with access to the branch but not the parent should not be able to use the parent peppol connection
        """
        _parent_company, branch_spoiled, _branch_independent = self._get_branch_companies_setup()
        poor_user = self.env['res.users'].create([{
            'name': "Poor User",
            'login': 'poor_user',
            'company_id': branch_spoiled.id,
            'company_ids': [(6, 0, [branch_spoiled.id])],
        }])
        wizard_spoiled = self.env['peppol.registration'].with_company(branch_spoiled).with_user(poor_user).sudo().create([{}])
        self.assertEqual(wizard_spoiled.use_parent_connection_selection, 'use_self')
        with self.assertRaises(AccessError):
            # This should never happen as the `use_parent_connection` field will be readonly,
            # but in case it happen, it should raise an AccessError.
            wizard_spoiled.use_parent_connection_selection = 'use_parent'
            wizard_spoiled.with_user(poor_user).button_register_peppol_participant()

    def test_peppol_branch_independent_registration(self):
        """
        Register branch_independent to use their own new peppol connection.
        """
        parent_company, _branch_spoiled, branch_independent = self._get_branch_companies_setup()
        wizard_independent_values = {
            'peppol_eas': '0208',
            'peppol_endpoint': '0239843188',
            'contact_email': 'branchindependent@odoo.com',
            'phone_number': '+32123456789',
        }

        # register branch_independent to use their own new connection
        wizard_independent = self.env['peppol.registration'].with_company(branch_independent).create([{
            'use_parent_connection_selection': 'use_self',
        }])
        self.assertRecordValues(wizard_independent, [{
            'active_parent_company': parent_company.id,
            'active_parent_company_name': parent_company.name,
            'is_branch_company': True,
            'selected_company_id': branch_independent.id,
            'peppol_eas': '0208',  # default peppol_eas for belgian company
            'peppol_endpoint': False,
            'contact_email': False,
            'phone_number': False,
        }])
        with patch('odoo.addons.account_peppol.models.res_company.ResCompany._sanitize_peppol_phone_number'):
            # prevent raising from setting bad/fake phone numbers; just for testing
            wizard_independent.write(wizard_independent_values)

        with self._patch_register_proxy_user_id_client('b'):
            wizard_independent.button_register_peppol_participant()

        self.assertRecordValues(branch_independent, [{
            'peppol_parent_company_id': False,
            'peppol_eas': wizard_independent['peppol_eas'],
            'peppol_endpoint': wizard_independent['peppol_endpoint'],
            'account_peppol_contact_email': wizard_independent['contact_email'],
            'account_peppol_phone_number': wizard_independent['phone_number'],
        }])
