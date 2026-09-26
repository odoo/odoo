<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
from base64 import b64encode
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
import json
from contextlib import contextmanager
from freezegun import freeze_time
from requests import Session, PreparedRequest, Response
from unittest.mock import patch
from urllib.parse import parse_qs, quote_plus
from psycopg2 import IntegrityError
=======
from contextlib import contextmanager
from freezegun import freeze_time
from requests import Session, PreparedRequest, Response
from unittest.mock import patch
from urllib.parse import parse_qs, quote_plus
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.form import Form
from odoo.tests.common import tagged, TransactionCase, freeze_time
from odoo.tools import mute_logger
from odoo.tools.misc import file_open
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
from odoo.exceptions import ValidationError, UserError
from odoo.tests import Form
from odoo.tests.common import tagged, TransactionCase
from odoo.tools import mute_logger
=======
from odoo.exceptions import ValidationError
from odoo.tests import Form
from odoo.tests.common import tagged, TransactionCase
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

from odoo.addons.account_peppol.tests.common import PeppolConnectorCommon


@freeze_time('2023-01-01')
@tagged('-at_install', 'post_install')
class TestPeppolParticipant(PeppolConnectorCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('account_peppol.edi.mode', 'test')
        cls.private_key = cls.env['certificate.key'].create({
            'name': 'Test key PEPPOL',
            'content': b64encode(file_open('account_peppol/tests/assets/private_key.pem', 'rb').read()),
        })

<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
        cls.env.company.write({
            'peppol_eas': '0208',
            'peppol_endpoint': '0239843188',
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
    @classmethod
    def _get_mock_responses(cls, peppol_state='active'):
        return {
            '/api/peppol/1/participant_status': {
                'result': {
                    'peppol_state': peppol_state,
                }
            },
            '/api/peppol/1/activate_participant': {'result': {}},
            '/api/peppol/1/register_sender': {'result': {}},
            '/iap/account_edi/2/create_user': {
                'result': {
                    'id_client': cls.env.context.get('mock_id_client', ID_CLIENT),
                    'refresh_token': FAKE_UUID,
                }
            },
            '/api/peppol/1/send_verification_code': {'result': {}},
            '/api/peppol/1/update_user': {'result': {}},
            '/api/peppol/1/verify_phone_number': {'result': {}},
            '/api/peppol/1/migrate_peppol_registration': {
                'result': {
                    'migration_key': 'test_key',
                }
            },
            '/api/peppol/1/get_all_documents': {'result': {'messages': []}},
        }

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        response = Response()
        response.status_code = 200

        # mock SMP participant lookup: 200 if pid in SMP_OK_IDS, else 404
        if r.path_url.startswith('/api/peppol/1/lookup'):
            peppol_identifier = parse_qs(r.path_url.rsplit('?')[1])['peppol_identifier'][0]
            if peppol_identifier in SMP_OK_IDS:
                response.json = lambda: {
                    "result": {
                        "identifier": peppol_identifier,
                        "smp_base_url": "http://example.com/smp",
                        "ttl": 60,
                        "service_group_url": "http://example.com/smp/iso6523-actorid-upis%3A%3A" + quote_plus(peppol_identifier),
                        "services": []
                    }
                }
            else:
                response.status_code = 404
                response.json = lambda: {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "no naptr record",
                        "retryable": False,
                    },
                }
            return response

        url = r.path_url
        body = json.loads(r.body)

        if custom_responses_by_id := cls.env.context.get('custom_responses_by_id'):
            identification = r.headers.get('odoo-edi-client-id', None)
            if identification and identification in custom_responses_by_id:
                response.json = lambda: custom_responses_by_id[identification]
                return response

        responses = cls._get_mock_responses(cls.env.context.get('peppol_state', 'active'))
        if (
            url == '/api/peppol/1/activate_participant'
            and cls.env.context.get('migrate_to')
            and not body['params']['migration_key']
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
            'account_peppol_eas': '9925',
            'account_peppol_endpoint': '0000000000',
=======
    @classmethod
    def _get_mock_responses(cls, peppol_state='active'):
        return {
            '/api/peppol/1/participant_status': {
                'result': {
                    'peppol_state': peppol_state,
                }
            },
            '/api/peppol/1/activate_participant': {'result': {}},
            '/api/peppol/1/register_sender': {'result': {}},
            '/iap/account_edi/2/create_user': {
                'result': {
                    'id_client': cls.env.context.get('mock_id_client', ID_CLIENT),
                    'refresh_token': FAKE_UUID,
                }
            },
            '/api/peppol/1/send_verification_code': {'result': {}},
            '/api/peppol/1/update_user': {'result': {}},
            '/api/peppol/1/verify_phone_number': {'result': {}},
            '/api/peppol/1/migrate_peppol_registration': {
                'result': {
                    'migration_key': 'test_key',
                }
            },
            '/api/peppol/1/get_all_documents': {'result': {'messages': []}},
        }

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        response = Response()
        response.status_code = 200

        # mock SMP participant lookup: 200 if pid in SMP_OK_IDS, else 404
        if r.path_url.startswith('/api/peppol/1/lookup'):
            peppol_identifier = parse_qs(r.path_url.rsplit('?')[1])['peppol_identifier'][0]
            if peppol_identifier in SMP_OK_IDS:
                response.json = lambda: {
                    "result": {
                        "identifier": peppol_identifier,
                        "smp_base_url": "http://example.com/smp",
                        "ttl": 60,
                        "service_group_url": "http://example.com/smp/iso6523-actorid-upis%3A%3A" + quote_plus(peppol_identifier),
                        "services": []
                    }
                }
            else:
                response.status_code = 404
                response.json = lambda: {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "no naptr record",
                        "retryable": False,
                    },
                }
            return response

        if r.path_url.startswith('/api/peppol/2/can_connect'):
            response.json = lambda: cls.env.context.get('can_connect_response', {'auth_required': False})
            return response

        url = r.path_url

        if url == '/api/peppol/2/connect':
            response.json = lambda: {
                'id_client': cls.env.context.get('mock_id_client', ID_CLIENT),
                'refresh_token': FAKE_UUID,
                'peppol_state': cls.env.context.get('connect_state', 'smp_registration'),
            }
            return response

        if custom_responses_by_id := cls.env.context.get('custom_responses_by_id'):
            identification = r.headers.get('odoo-edi-client-id', None)
            if identification and identification in custom_responses_by_id:
                response.json = lambda: custom_responses_by_id[identification]
                return response

        responses = cls._get_mock_responses(cls.env.context.get('peppol_state', 'active'))

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
            'account_peppol_eas': '9925',
            'account_peppol_endpoint': '0000000000',
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a
            'account_peppol_phone_number': '+32483123456',
            'account_peppol_contact_email': 'yourcompany@test.example.com',
        })

    def test_ignore_archived_edi_users(self):
        wizard = self.env['peppol.registration'].create({})
        with self._mock_requests([
            self._mock_create_user(),
            self._mock_lookup_participant(),
            self._mock_register_sender(),
        ]):
            wizard.button_peppol_sender_registration()

        self.env['account_edi_proxy_client.user'].create([{
            'active': False,
            'id_client': f'client-demo',
            'company_id': self.env.company.id,
            'edi_identification': f'client-demo',
            'private_key_id': self.env['certificate.key'].sudo()._generate_rsa_private_key(self.env.company).id,
            'refresh_token': False,
            'proxy_type': 'peppol',
            'edi_mode': 'demo',
        }])
        with self._mock_requests([
            self._mock_lookup_participant(),
        ]):
            self.env.company.with_context(active_test=False).partner_id.button_account_peppol_check_partner_endpoint()

    def test_create_participant_missing_data(self):
        # creating a participant without eas/endpoint/document should not be possible
        wizard = self.env['peppol.registration'].create({
            'peppol_eas': False,
            'peppol_endpoint': False,
        })
        with self.assertRaises(ValidationError), self.cr.savepoint():
<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
            wizard.button_peppol_sender_registration()
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
            settings.button_create_peppol_proxy_user()
=======
            settings.button_register_with_kyc()
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
    def test_register_participant_for_the_first_time_as_sender_then_receiver_then_unregister(self):
        # not_register -> sender
        with self._mock_requests([
            self._mock_create_user(),
            self._mock_lookup_participant(already_exist=True),
            self._mock_register_sender(),
        ]):
            wizard = self.env['peppol.registration'].create({})
            self.assertRecordValues(wizard, [{'smp_registration': False}])
            wizard.button_register_peppol_participant()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'sender'}])
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
    def test_create_success_participant(self):
        # should be possible to apply with all data
        # the account_peppol_proxy_state should correctly change to pending
        # then the account_peppol_proxy_state should change success
        # after checking participant status
        company = self.env.company
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        self.assertEqual(company.account_peppol_proxy_state, 'not_verified')
        settings.button_send_peppol_verification_code()
        self.assertEqual(company.account_peppol_proxy_state, 'sent_verification')
        settings.account_peppol_verification_code = '123456'
        settings.button_check_peppol_verification_code()
        self.assertEqual(company.account_peppol_proxy_state, 'pending')
        self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
        self.assertEqual(company.account_peppol_proxy_state, 'active')
=======
    def test_create_success_participant(self):
        # the proxy state follows the state returned by /2/connect,
        # then changes to active after checking participant status
        company = self.env.company
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_register_with_kyc()
        self.assertEqual(company.account_peppol_proxy_state, 'pending')
        self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
        self.assertEqual(company.account_peppol_proxy_state, 'active')

    def test_create_success_participant_deprecated_flow(self):
        # button_create_peppol_proxy_user is no longer reachable from the interface,
        # but it and the phone verification are still covered here
        company = self.env.company
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        self.assertEqual(company.account_peppol_proxy_state, 'not_verified')
        settings.button_send_peppol_verification_code()
        self.assertEqual(company.account_peppol_proxy_state, 'sent_verification')
        settings.account_peppol_verification_code = '123456'
        settings.button_check_peppol_verification_code()
        self.assertEqual(company.account_peppol_proxy_state, 'pending')
        self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
        self.assertEqual(company.account_peppol_proxy_state, 'active')
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
        # sender -> smp_registration.
        settings = self.env['res.config.settings'].create({})
        with self._mock_requests([
            self._mock_lookup_participant(),
            self._mock_register_sender_as_receiver(),
        ]):
            settings.button_peppol_smp_registration()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'smp_registration'}])
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
    def test_create_reject_participant(self):
        # the account_peppol_proxy_state should change to rejected
        # if we reject the participant
        company = self.env.company
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
=======
    def test_create_participant_authentication_required(self):
        # when the proxy requires KYC, the button redirects and nothing is created yet
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        with self._set_context({'can_connect_response': {
            'auth_required': True,
            'available_auths': {'generic': {'authorization_url': 'https://peppol.test.odoo.com/kyc'}},
        }}):
            action = settings.button_register_with_kyc()

        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertEqual(action['url'], 'https://peppol.test.odoo.com/kyc')
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'not_registered')
        self.assertFalse(self.env.company.account_edi_proxy_client_ids)

    def test_connect_token(self):
        # the callback and the webhook get the company through this token
        company = self.env.company
        token = company._peppol_generate_connect_token('9925:0000000000')
        connect_data = self.env['res.company']._peppol_decode_connect_token(token)
        self.assertEqual(connect_data['company'], company)
        self.assertEqual(connect_data['peppol_identifier'], '9925:0000000000')
        self.assertFalse(self.env['res.company']._peppol_decode_connect_token('not-a-token'))

    def test_create_reject_participant(self):
        # the account_peppol_proxy_state should change to rejected
        # if we reject the participant
        company = self.env.company
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
        # smp_registration -> receiver.
        with self._mock_requests([self._mock_participant_status('receiver')]):
            self.env.company.account_edi_proxy_client_ids._peppol_get_participant_status()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'receiver'}])
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
        with self._set_context({'peppol_state': 'rejected'}):
            settings.button_create_peppol_proxy_user()
            company.account_peppol_proxy_state = 'pending'
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(company.account_peppol_proxy_state, 'rejected')
=======
        with self._set_context({'peppol_state': 'rejected'}):
            settings.button_register_with_kyc()
            company.account_peppol_proxy_state = 'pending'
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(company.account_peppol_proxy_state, 'rejected')
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
        # receiver -> not_registered.
        with self._mock_requests([
            self._mock_participant_status('receiver'),
            self._mock_get_all_documents(),
            self._mock_cancel_peppol_registration(),
        ]):
            wizard = self.env['peppol.registration'].create({})
            wizard.button_deregister_peppol_participant()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'not_registered'}])

    def test_register_participant_already_exists_on_peppol_as_receiver(self):
        # not_register -> smp_registration
        with self._mock_requests([
            self._mock_create_user(),
            self._mock_lookup_participant(),
            self._mock_register_sender(),
        ]):
            wizard = self.env['peppol.registration'].create({})
            self.assertRecordValues(wizard, [{'smp_registration': True}])
            wizard.button_register_peppol_participant()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'smp_registration'}])

        # smp_registration -> receiver
        with self._mock_requests([self._mock_participant_status('receiver')]):
            self.env.company.account_edi_proxy_client_ids._peppol_get_participant_status()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'receiver'}])

    def test_register_participant_rejected(self):
        # not_register -> smp_registration
        with self._mock_requests([
            self._mock_create_user(),
            self._mock_lookup_participant(),
            self._mock_register_sender(),
        ]):
            wizard = self.env['peppol.registration'].create({})
            self.assertRecordValues(wizard, [{'smp_registration': True}])
            wizard.button_register_peppol_participant()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'smp_registration'}])

        # smp_registration -> rejected
        with self._mock_requests([self._mock_participant_status('rejected')]):
            self.env.company.account_edi_proxy_client_ids._peppol_get_participant_status()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'rejected'}])
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
    @mute_logger('odoo.sql_db')
    def test_create_duplicate_participant(self):
        # should not be possible to create a duplicate participant
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            settings.account_peppol_proxy_state = 'not_registered'
            settings.button_create_peppol_proxy_user()
=======
    def test_recreate_participant_archives_the_previous_user(self):
        # only one active user per company is allowed, registering again archives the old one
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_register_with_kyc()
        first_user = self.env.company.account_edi_proxy_client_ids
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
    def test_save_migration_key(self):
        """ Ensure the migration_key is remove from the company after we've used it. """
        with self._mock_requests([
            self._mock_create_user(),
            self._mock_register_sender(),
        ]):
            wizard = self.env['peppol.registration'].create({
                'account_peppol_migration_key': 'helloo',
            })
            wizard.button_register_peppol_participant()
            self.assertRecordValues(self.env.company, [{
                'account_peppol_proxy_state': 'smp_registration',
                'account_peppol_migration_key': False,
            }])
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
    def test_save_migration_key(self):
        # migration key should be saved
        settings = self.env['res.config.settings']\
            .create({
                **self._get_participant_vals(),
                'account_peppol_migration_key': 'helloo',
            })
=======
        settings.account_peppol_proxy_state = 'not_registered'
        with self._set_context({'mock_id_client': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxy'}):
            settings.button_register_with_kyc()
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
    def test_peppol_registration_register_as_self(self):
        self.env.company.write({'child_ids': [Command.create({'name': 'Branch A'})]})
        branch = self.env.company.child_ids
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
        with self._set_context({'migrate_to': True}):
            settings.button_create_peppol_proxy_user()
            self.assertEqual(self.env.company.account_peppol_proxy_state, 'not_verified')
            self.assertFalse(settings.account_peppol_migration_key)  # the key should be reset once we've used it
=======
        self.assertFalse(first_user.active)
        self.assertEqual(len(self.env.company.account_edi_proxy_client_ids), 1)
        self.assertEqual(self.env.company.account_edi_proxy_client_ids.id_client, 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxy')
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
        settings = self.env['res.config.settings'].with_context(allowed_company_ids=branch.ids).create({})
        self.assertRecordValues(settings, [{
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
    def test_restore_simple(self):
        """Test basic recovery: create user, soft-delete it, then recover it"""
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        edi_user = self.env.company.account_edi_proxy_client_ids

        # Simulate soft-delete (what happened during incident)
        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        # Recovery should reactivate the user and update company state
        self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(edi_user.company_id)
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'active')
        self.assertTrue(edi_user.active)

    def test_restore_ignores_multi_user_companies(self):
        """Test safety: don't recover when multiple inactive users exist (ambiguous)"""
        # Create first user and soft-delete it
        user_1_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000000'}
        self.env['res.config.settings'].create(user_1_vals).button_create_peppol_proxy_user()

        active_user = self.env.company.account_edi_proxy_client_ids
        active_user.active = False
        active_user.company_id.account_peppol_proxy_state = 'not_registered'

        # Create second user and soft-delete it too
        user_2_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000001'}
        with self._set_context({'mock_id_client': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxy'}):
            self.env['res.config.settings'].create(user_2_vals).button_create_peppol_proxy_user()
        edi_user_2 = self.env.company.account_edi_proxy_client_ids
        edi_user_2.active = False
        edi_user_2.company_id.account_peppol_proxy_state = 'not_registered'

        # Recovery should do nothing when multiple users exist
        result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(self.env.company)
        self.assertIsNone(result)
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'not_registered')
        self.assertFalse(any((active_user | edi_user_2).mapped('active')))

    def test_restore_recovery_during_registration_same_endpoint(self):
        """Test main incident scenario: recovery happens during new registration attempt"""
        user_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000000'}
        self.env['res.config.settings'].create(user_vals).button_create_peppol_proxy_user()
        edi_user = self.env.company.account_edi_proxy_client_ids

        # simulate incident: user gets soft-deleted
        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        # user tries to re-register with same endpoint -> recovery kicks in
        self.env['res.config.settings'].create(user_vals).button_create_peppol_proxy_user()

        # should recover existing user instead of creating new one
        self.assertEqual(edi_user.edi_identification, '9925:0000000000')
        self.assertEqual(edi_user.company_id.account_peppol_proxy_state, 'active')
        self.assertTrue(edi_user.active)

    def test_restore_skip_when_active_user_exists(self):
        """Recovery should be skipped when an active PEPPOL user already exists"""
        # create active user first
        user_1_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000000'}
        self.env['res.config.settings'].create(user_1_vals).button_create_peppol_proxy_user()
        inactive_user = self.env.company.account_edi_proxy_client_ids
        inactive_user.active = False
        inactive_user.company_id.account_peppol_proxy_state = 'not_registered'

        # create second user that gets soft-deleted
        user_2_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000001'}
        with self._set_context({'mock_id_client': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxy'}):
            self.env['res.config.settings'].create(user_2_vals).button_create_peppol_proxy_user()

        active_user = self.env.company.account_edi_proxy_client_ids.filtered(lambda u: u.edi_identification == '9925:0000000001')
        active_user.active = False

        # recovery should skip inactive user since active one exists
        result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(self.env.company)
        self.assertIsNone(result)
        self.assertFalse(inactive_user.active)

    def test_restore_with_specific_identifier(self):
        """Recovery with specific identifier should only recover that user"""
        # create first user and soft-delete it
        user_1_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000000'}
        self.env['res.config.settings'].create(user_1_vals).button_create_peppol_proxy_user()
        edi_user_1 = self.env.company.account_edi_proxy_client_ids
        edi_user_1.active = False
        edi_user_1.company_id.account_peppol_proxy_state = 'not_registered'

        # create second user and soft-delete it
        user_2_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000001'}
        with self._set_context({'mock_id_client': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxy'}):
            self.env['res.config.settings'].create(user_2_vals).button_create_peppol_proxy_user()
        edi_user_2 = self.env.company.account_edi_proxy_client_ids.filtered(lambda u: u.edi_identification == '9925:0000000001')
        edi_user_2.active = False
        edi_user_2.company_id.account_peppol_proxy_state = 'not_registered'

        # recovery with specific identifier should only recover user_2
        result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(
            self.env.company, peppol_identifier='9925:0000000001'
        )

        self.assertEqual(result, edi_user_2)
        self.assertTrue(edi_user_2.active)
        self.assertFalse(edi_user_1.active)

    def test_restore_user_in_draft_state(self):
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        edi_user = self.env.company.account_edi_proxy_client_ids

        # simulate soft-delete
        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        # mock IAP returning draft state
        with self._set_context({'peppol_state': 'active'}):
            user_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000000'}
            # user tries to re-register with same endpoint -> recovery kicks in
            self.env['res.config.settings'].create(user_vals).button_create_peppol_proxy_user()

        # should recover user and set state to active
        self.assertTrue(edi_user.active)
        self.assertEqual(edi_user.company_id.account_peppol_proxy_state, 'active')

    def test_cron_recovery_multi_company(self):
        """Test cron recovery works correctly across multi companies"""
        # create users for both companies
        settings_1 = self.env['res.config.settings'].create(self._get_participant_vals())
        settings_1.button_create_peppol_proxy_user()
        edi_user_1 = self.env.company.account_edi_proxy_client_ids

        company_2 = self.env['res.company'].create({
            'name': 'Test Company 2',
            'peppol_eas': '9925',
            'peppol_endpoint': '0000000001',
        })
        with self._set_context({'mock_id_client': 'company2-client-id'}):
            settings_2 = self.env['res.config.settings'].with_company(company_2).create({
                'account_peppol_eas': '9925',
                'account_peppol_endpoint': '0000000001',
                'account_peppol_phone_number': '+32483123456',
                'account_peppol_contact_email': 'company2@test.example.com',
            })
            settings_2.button_create_peppol_proxy_user()
        edi_user_2 = company_2.account_edi_proxy_client_ids

        # soft-delete both users
        (edi_user_1 | edi_user_2).active = False
        (edi_user_1 | edi_user_2).company_id.account_peppol_proxy_state = 'not_registered'

        # run cron. this should recover both users
        self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()

        self.assertTrue(edi_user_1.active)
        self.assertTrue(edi_user_2.active)
        self.assertEqual(edi_user_1.company_id.account_peppol_proxy_state, 'active')
        self.assertEqual(edi_user_2.company_id.account_peppol_proxy_state, 'active')

    def test_cron_recovery_mixed_companies(self):
        """Test cron handles mixed scenarios: some recoverable, some not"""
        # company1: one inactive user (recoverable)
        settings_1 = self.env['res.config.settings'].create(self._get_participant_vals())
        settings_1.button_create_peppol_proxy_user()
        edi_user_1 = self.env.company.account_edi_proxy_client_ids
        edi_user_1.active = False
        edi_user_1.company_id.account_peppol_proxy_state = 'not_registered'

        # company 2: multiple inactive users (not recoverable)
        company_2 = self.env['res.company'].create({
            'name': 'Test Company 2',
            'peppol_eas': '9925',
            'peppol_endpoint': '2222222222',
        })

        with self._set_context({'mock_id_client': 'company2-user1'}):
            settings_2a = self.env['res.config.settings'].with_company(company_2).create({
                'account_peppol_eas': '9925',
                'account_peppol_endpoint': '2222222222',
                'account_peppol_phone_number': '+32483123456',
                'account_peppol_contact_email': 'company2a@test.example.com',
            })
            settings_2a.button_create_peppol_proxy_user()
            company_2.account_edi_proxy_client_ids.active = False
            company_2.account_peppol_proxy_state = 'not_registered'

        with self._set_context({'mock_id_client': 'company2-user2'}):
            settings_2b = self.env['res.config.settings'].with_company(company_2).create({
                'account_peppol_eas': '9925',
                'account_peppol_endpoint': '3333333333',
                'account_peppol_phone_number': '+32483123456',
                'account_peppol_contact_email': 'company2b@test.example.com',
            })
            settings_2b.button_create_peppol_proxy_user()
            company_2.account_edi_proxy_client_ids.active = False
            company_2.account_peppol_proxy_state = 'not_registered'

        self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()

        # company1 should recover
        self.assertTrue(edi_user_1.active)
        self.assertEqual(edi_user_1.company_id.account_peppol_proxy_state, 'active')

        # company2 should not recover (multiple users)
        company_2_users = company_2.with_context(active_test=False).account_edi_proxy_client_ids
        self.assertEqual(len(company_2_users), 2)
        self.assertFalse(any(company_2_users.mapped('active')))
        self.assertEqual(company_2.account_peppol_proxy_state, 'not_registered')

    def test_recovery_error_handling(self):
        """make sure recovery handles API errors gracefully"""
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        edi_user = self.env.company.account_edi_proxy_client_ids

        # simulate soft-delete
        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        # Mock API error during participant_status call
        with self._set_context({'migrated_away': True}):  # mocks no_such_user response
            result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(edi_user.company_id)

        # would have to handle error gracefully
        self.assertIsNone(result)
        self.assertFalse(edi_user.active)

    def test_recovery_no_refresh_token(self):
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        edi_user = self.env.company.account_edi_proxy_client_ids

        # Simulate soft-delete and remove refresh token
        edi_user.write({
            'active': False,
            'refresh_token': False,
        })
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(edi_user.company_id)

        # Should not recover user without refresh token
        self.assertIsNone(result)
        self.assertFalse(edi_user.active)

    def test_recovery_demo_mode_skip(self):
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        edi_user = self.env.company.account_edi_proxy_client_ids
        edi_user.edi_mode = 'demo'

        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(edi_user.company_id)

        # Should not recover demo mode users
        self.assertIsNone(result)
        self.assertFalse(edi_user.active)

    def test_recovery_unknown_peppol_state(self):
        """Test recovery handles unknown peppol states gracefully"""
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        edi_user = self.env.company.account_edi_proxy_client_ids

        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        # Mock unknown state from IAP
        with self._set_context({'peppol_state': 'unknown_future_state'}):
            result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(edi_user.company_id)

        # handle anything gracefully to avoid disrupting existing flows
        self.assertIsNone(result)
        self.assertFalse(edi_user.active)
        self.assertEqual(edi_user.company_id.account_peppol_proxy_state, 'not_registered')

    def test_recovery_multiple_companies_batch_error(self):
        """Test cron handles errors in one company without affecting others"""
        # company_1: normal recoverable user
        settings_1 = self.env['res.config.settings'].create(self._get_participant_vals())
        settings_1.button_create_peppol_proxy_user()
        edi_user_1 = self.env.company.account_edi_proxy_client_ids
        edi_user_1.active = False
        edi_user_1.company_id.account_peppol_proxy_state = 'not_registered'

        # company_2: user that will cause API error
        company_2 = self.env['res.company'].create({
            'name': 'Test Company 2',
            'peppol_eas': '9925',
            'peppol_endpoint': '1111111111',
        })

        with self._set_context({'mock_id_client': 'error-client-id'}):
            settings_2 = self.env['res.config.settings'].with_company(company_2).create({
                'account_peppol_eas': '9925',
                'account_peppol_endpoint': '1111111111',
                'account_peppol_phone_number': '+32483123456',
                'account_peppol_contact_email': 'company2@test.example.com',
            })
            settings_2.button_create_peppol_proxy_user()

        edi_user_2 = company_2.account_edi_proxy_client_ids
        edi_user_2.active = False
        edi_user_2.company_id.account_peppol_proxy_state = 'not_registered'

        with self._set_context({
            'custom_responses_by_id': {
                'error-client-id': {  # Company 2 gets error
                    'result': {
                        'proxy_error': {
                            'code': 'no_such_user',
                            'message': 'User not found'
                        }
                    }
                }
                # Company 1 uses default active response
            }
        }):
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()

            # company 1 should recover despite company 2 error
            self.assertTrue(edi_user_1.active)
            self.assertEqual(edi_user_1.company_id.account_peppol_proxy_state, 'active')

            # company 2 should not recover due to error
            self.assertFalse(edi_user_2.active)
            self.assertEqual(company_2.account_peppol_proxy_state, 'not_registered')

    def test_recovery_company_with_migration_key_skip(self):
        """Test recovery skips companies with migration keys"""
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        edi_user = self.env.company.account_edi_proxy_client_ids

        # simulate soft-delete with migration key
        edi_user.active = False
        edi_user.company_id.write({
=======
    def test_restore_simple(self):
        """Test basic recovery: create user, soft-delete it, then recover it"""
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_register_with_kyc()
        edi_user = self.env.company.account_edi_proxy_client_ids

        # Simulate soft-delete (what happened during incident)
        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        # Recovery should reactivate the user and update company state
        self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(edi_user.company_id)
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'active')
        self.assertTrue(edi_user.active)

    def test_restore_ignores_multi_user_companies(self):
        """Test safety: don't recover when multiple inactive users exist (ambiguous)"""
        # Create first user and soft-delete it
        user_1_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000000'}
        self.env['res.config.settings'].create(user_1_vals).button_register_with_kyc()

        active_user = self.env.company.account_edi_proxy_client_ids
        active_user.active = False
        active_user.company_id.account_peppol_proxy_state = 'not_registered'

        # Create second user and soft-delete it too
        user_2_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000001'}
        with self._set_context({'mock_id_client': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxy'}):
            self.env['res.config.settings'].create(user_2_vals).button_register_with_kyc()
        edi_user_2 = self.env.company.account_edi_proxy_client_ids
        edi_user_2.active = False
        edi_user_2.company_id.account_peppol_proxy_state = 'not_registered'

        # Recovery should do nothing when multiple users exist
        result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(self.env.company)
        self.assertIsNone(result)
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'not_registered')
        self.assertFalse(any((active_user | edi_user_2).mapped('active')))

    def test_restore_recovery_during_registration_same_endpoint(self):
        """Test main incident scenario: recovery happens during new registration attempt"""
        user_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000000'}
        self.env['res.config.settings'].create(user_vals).button_register_with_kyc()
        edi_user = self.env.company.account_edi_proxy_client_ids

        # simulate incident: user gets soft-deleted
        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        # user tries to re-register with same endpoint -> recovery kicks in
        self.env['res.config.settings'].create(user_vals).button_register_with_kyc()

        # should recover existing user instead of creating new one
        self.assertEqual(edi_user.edi_identification, '9925:0000000000')
        self.assertEqual(edi_user.company_id.account_peppol_proxy_state, 'active')
        self.assertTrue(edi_user.active)

    def test_restore_skip_when_active_user_exists(self):
        """Recovery should be skipped when an active PEPPOL user already exists"""
        # create active user first
        user_1_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000000'}
        self.env['res.config.settings'].create(user_1_vals).button_register_with_kyc()
        inactive_user = self.env.company.account_edi_proxy_client_ids
        inactive_user.active = False
        inactive_user.company_id.account_peppol_proxy_state = 'not_registered'

        # create second user that gets soft-deleted
        user_2_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000001'}
        with self._set_context({'mock_id_client': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxy'}):
            self.env['res.config.settings'].create(user_2_vals).button_register_with_kyc()

        active_user = self.env.company.account_edi_proxy_client_ids.filtered(lambda u: u.edi_identification == '9925:0000000001')
        active_user.active = False

        # recovery should skip inactive user since active one exists
        result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(self.env.company)
        self.assertIsNone(result)
        self.assertFalse(inactive_user.active)

    def test_restore_with_specific_identifier(self):
        """Recovery with specific identifier should only recover that user"""
        # create first user and soft-delete it
        user_1_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000000'}
        self.env['res.config.settings'].create(user_1_vals).button_register_with_kyc()
        edi_user_1 = self.env.company.account_edi_proxy_client_ids
        edi_user_1.active = False
        edi_user_1.company_id.account_peppol_proxy_state = 'not_registered'

        # create second user and soft-delete it
        user_2_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000001'}
        with self._set_context({'mock_id_client': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxy'}):
            self.env['res.config.settings'].create(user_2_vals).button_register_with_kyc()
        edi_user_2 = self.env.company.account_edi_proxy_client_ids.filtered(lambda u: u.edi_identification == '9925:0000000001')
        edi_user_2.active = False
        edi_user_2.company_id.account_peppol_proxy_state = 'not_registered'

        # recovery with specific identifier should only recover user_2
        result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(
            self.env.company, peppol_identifier='9925:0000000001'
        )

        self.assertEqual(result, edi_user_2)
        self.assertTrue(edi_user_2.active)
        self.assertFalse(edi_user_1.active)

    def test_restore_user_in_draft_state(self):
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_register_with_kyc()
        edi_user = self.env.company.account_edi_proxy_client_ids

        # simulate soft-delete
        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        # mock IAP returning draft state
        with self._set_context({'peppol_state': 'active'}):
            user_vals = {**self._get_participant_vals(), 'account_peppol_endpoint': '0000000000'}
            # user tries to re-register with same endpoint -> recovery kicks in
            self.env['res.config.settings'].create(user_vals).button_register_with_kyc()

        # should recover user and set state to active
        self.assertTrue(edi_user.active)
        self.assertEqual(edi_user.company_id.account_peppol_proxy_state, 'active')

    def test_cron_recovery_multi_company(self):
        """Test cron recovery works correctly across multi companies"""
        # create users for both companies
        settings_1 = self.env['res.config.settings'].create(self._get_participant_vals())
        settings_1.button_register_with_kyc()
        edi_user_1 = self.env.company.account_edi_proxy_client_ids

        company_2 = self.env['res.company'].create({
            'name': 'Test Company 2',
            'peppol_eas': '9925',
            'peppol_endpoint': '0000000001',
        })
        with self._set_context({'mock_id_client': 'company2-client-id'}):
            settings_2 = self.env['res.config.settings'].with_company(company_2).create({
                'account_peppol_eas': '9925',
                'account_peppol_endpoint': '0000000001',
                'account_peppol_phone_number': '+32483123456',
                'account_peppol_contact_email': 'company2@test.example.com',
            })
            settings_2.button_register_with_kyc()
        edi_user_2 = company_2.account_edi_proxy_client_ids

        # soft-delete both users
        (edi_user_1 | edi_user_2).active = False
        (edi_user_1 | edi_user_2).company_id.account_peppol_proxy_state = 'not_registered'

        # run cron. this should recover both users
        self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()

        self.assertTrue(edi_user_1.active)
        self.assertTrue(edi_user_2.active)
        self.assertEqual(edi_user_1.company_id.account_peppol_proxy_state, 'active')
        self.assertEqual(edi_user_2.company_id.account_peppol_proxy_state, 'active')

    def test_cron_recovery_mixed_companies(self):
        """Test cron handles mixed scenarios: some recoverable, some not"""
        # company1: one inactive user (recoverable)
        settings_1 = self.env['res.config.settings'].create(self._get_participant_vals())
        settings_1.button_register_with_kyc()
        edi_user_1 = self.env.company.account_edi_proxy_client_ids
        edi_user_1.active = False
        edi_user_1.company_id.account_peppol_proxy_state = 'not_registered'

        # company 2: multiple inactive users (not recoverable)
        company_2 = self.env['res.company'].create({
            'name': 'Test Company 2',
            'peppol_eas': '9925',
            'peppol_endpoint': '2222222222',
        })

        with self._set_context({'mock_id_client': 'company2-user1'}):
            settings_2a = self.env['res.config.settings'].with_company(company_2).create({
                'account_peppol_eas': '9925',
                'account_peppol_endpoint': '2222222222',
                'account_peppol_phone_number': '+32483123456',
                'account_peppol_contact_email': 'company2a@test.example.com',
            })
            settings_2a.button_register_with_kyc()
            company_2.account_edi_proxy_client_ids.active = False
            company_2.account_peppol_proxy_state = 'not_registered'

        with self._set_context({'mock_id_client': 'company2-user2'}):
            settings_2b = self.env['res.config.settings'].with_company(company_2).create({
                'account_peppol_eas': '9925',
                'account_peppol_endpoint': '3333333333',
                'account_peppol_phone_number': '+32483123456',
                'account_peppol_contact_email': 'company2b@test.example.com',
            })
            settings_2b.button_register_with_kyc()
            company_2.account_edi_proxy_client_ids.active = False
            company_2.account_peppol_proxy_state = 'not_registered'

        self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()

        # company1 should recover
        self.assertTrue(edi_user_1.active)
        self.assertEqual(edi_user_1.company_id.account_peppol_proxy_state, 'active')

        # company2 should not recover (multiple users)
        company_2_users = company_2.with_context(active_test=False).account_edi_proxy_client_ids
        self.assertEqual(len(company_2_users), 2)
        self.assertFalse(any(company_2_users.mapped('active')))
        self.assertEqual(company_2.account_peppol_proxy_state, 'not_registered')

    def test_recovery_error_handling(self):
        """make sure recovery handles API errors gracefully"""
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_register_with_kyc()
        edi_user = self.env.company.account_edi_proxy_client_ids

        # simulate soft-delete
        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        # Mock API error during participant_status call
        with self._set_context({'migrated_away': True}):  # mocks no_such_user response
            result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(edi_user.company_id)

        # would have to handle error gracefully
        self.assertIsNone(result)
        self.assertFalse(edi_user.active)

    def test_recovery_no_refresh_token(self):
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_register_with_kyc()
        edi_user = self.env.company.account_edi_proxy_client_ids

        # Simulate soft-delete and remove refresh token
        edi_user.write({
            'active': False,
            'refresh_token': False,
        })
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(edi_user.company_id)

        # Should not recover user without refresh token
        self.assertIsNone(result)
        self.assertFalse(edi_user.active)

    def test_recovery_demo_mode_skip(self):
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_register_with_kyc()
        edi_user = self.env.company.account_edi_proxy_client_ids
        edi_user.edi_mode = 'demo'

        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(edi_user.company_id)

        # Should not recover demo mode users
        self.assertIsNone(result)
        self.assertFalse(edi_user.active)

    def test_recovery_unknown_peppol_state(self):
        """Test recovery handles unknown peppol states gracefully"""
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_register_with_kyc()
        edi_user = self.env.company.account_edi_proxy_client_ids

        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        # Mock unknown state from IAP
        with self._set_context({'peppol_state': 'unknown_future_state'}):
            result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(edi_user.company_id)

        # handle anything gracefully to avoid disrupting existing flows
        self.assertIsNone(result)
        self.assertFalse(edi_user.active)
        self.assertEqual(edi_user.company_id.account_peppol_proxy_state, 'not_registered')

    def test_recovery_multiple_companies_batch_error(self):
        """Test cron handles errors in one company without affecting others"""
        # company_1: normal recoverable user
        settings_1 = self.env['res.config.settings'].create(self._get_participant_vals())
        settings_1.button_register_with_kyc()
        edi_user_1 = self.env.company.account_edi_proxy_client_ids
        edi_user_1.active = False
        edi_user_1.company_id.account_peppol_proxy_state = 'not_registered'

        # company_2: user that will cause API error
        company_2 = self.env['res.company'].create({
            'name': 'Test Company 2',
            'peppol_eas': '9925',
            'peppol_endpoint': '1111111111',
        })

        with self._set_context({'mock_id_client': 'error-client-id'}):
            settings_2 = self.env['res.config.settings'].with_company(company_2).create({
                'account_peppol_eas': '9925',
                'account_peppol_endpoint': '1111111111',
                'account_peppol_phone_number': '+32483123456',
                'account_peppol_contact_email': 'company2@test.example.com',
            })
            settings_2.button_register_with_kyc()

        edi_user_2 = company_2.account_edi_proxy_client_ids
        edi_user_2.active = False
        edi_user_2.company_id.account_peppol_proxy_state = 'not_registered'

        with self._set_context({
            'custom_responses_by_id': {
                'error-client-id': {  # Company 2 gets error
                    'result': {
                        'proxy_error': {
                            'code': 'no_such_user',
                            'message': 'User not found'
                        }
                    }
                }
                # Company 1 uses default active response
            }
        }):
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()

            # company 1 should recover despite company 2 error
            self.assertTrue(edi_user_1.active)
            self.assertEqual(edi_user_1.company_id.account_peppol_proxy_state, 'active')

            # company 2 should not recover due to error
            self.assertFalse(edi_user_2.active)
            self.assertEqual(company_2.account_peppol_proxy_state, 'not_registered')

    def test_recovery_company_with_migration_key_skip(self):
        """Test recovery skips companies with migration keys"""
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_register_with_kyc()
        edi_user = self.env.company.account_edi_proxy_client_ids

        # simulate soft-delete with migration key
        edi_user.active = False
        edi_user.company_id.write({
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a
            'account_peppol_proxy_state': 'not_registered',
            'peppol_use_parent_company': False,
        }])

        wizard = self.env['peppol.registration'].with_context(allowed_company_ids=branch.ids).create({})
        self.assertRecordValues(wizard, [{
            'company_id': branch.id,
            'parent_company_id': self.env.company.id,
            'selected_company_id': branch.id,
            'use_parent_connection_selection': 'use_self',
        }])

        # You must not use the same EAS/ENDPOINT than the parent company!
        wizard.write({
            'contact_email': "turlututu@tsointsoin.com",
            'phone_number': "+3236656565",
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
        })
        with self._mock_requests([
            self._mock_create_user(),
            self._mock_lookup_participant(already_exist=True),
            self._mock_register_sender(),
        ]):
            wizard.button_register_peppol_participant()

        self.assertRecordValues(branch, [{
            'peppol_parent_company_id': False,
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
            'account_peppol_contact_email': "turlututu@tsointsoin.com",
            'account_peppol_phone_number': "+3236656565",
        }])

        settings = self.env['res.config.settings'].with_context(allowed_company_ids=branch.ids).create({})
        self.assertRecordValues(settings, [{
            'account_peppol_proxy_state': 'sender',
            'peppol_use_parent_company': False,
        }])

<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
        # Disconnect from the network.
        with self._mock_requests([
            self._mock_participant_status('sender'),
            self._mock_cancel_peppol_registration(),
        ]):
            settings.button_deregister_peppol_participant()
        self.assertRecordValues(settings, [{
            'account_peppol_proxy_state': 'not_registered',
            'peppol_use_parent_company': False,
        }])
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
    def test_recovery_company_inconsistent_state_skip(self):
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        edi_user = self.env.company.account_edi_proxy_client_ids
=======
    def test_recovery_company_inconsistent_state_skip(self):
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_register_with_kyc()
        edi_user = self.env.company.account_edi_proxy_client_ids
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

        # Back to the initial state.
        wizard = self.env['peppol.registration'].with_context(allowed_company_ids=(branch + self.env.company).ids).create({})
        self.assertRecordValues(wizard, [{
            'company_id': branch.id,
            'parent_company_id': self.env.company.id,
            'selected_company_id': branch.id,
            'use_parent_connection_selection': 'use_self',
        }])

    def test_peppol_registration_register_as_parent(self):
        self.env.company.write({'child_ids': [Command.create({'name': 'Branch A'})]})
        branch = self.env.company.child_ids

        settings = self.env['res.config.settings'].with_context(allowed_company_ids=branch.ids).create({})
        self.assertRecordValues(settings, [{
            'account_peppol_proxy_state': 'not_registered',
            'peppol_use_parent_company': False,
        }])

<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
        # Check the initial state of the wizard for the branch.
        wizard = self.env['peppol.registration'].with_context(allowed_company_ids=(branch + self.env.company).ids).create({})
        self.assertRecordValues(wizard, [{
            'company_id': branch.id,
            'parent_company_id': self.env.company.id,
            'selected_company_id': branch.id,
            'use_parent_connection_selection': 'use_self',
            'peppol_eas': False,
            'peppol_endpoint': False,
            'phone_number': False,
            'contact_email': False,
        }])
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
    def test_recovery_malformed_response_handling(self):
        """Test recovery handles malformed API responses"""
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        with self._set_context({'mock_id_client': 'error-client-id'}):
            settings.button_create_peppol_proxy_user()
        edi_user = self.env.company.account_edi_proxy_client_ids
=======
    def test_recovery_malformed_response_handling(self):
        """Test recovery handles malformed API responses"""
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        with self._set_context({'mock_id_client': 'error-client-id'}):
            settings.button_register_with_kyc()
        edi_user = self.env.company.account_edi_proxy_client_ids
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

        # Register the parent company.
        wizard = self.env['peppol.registration'].with_context(allowed_company_ids=self.env.company.ids).create({})
        self.assertRecordValues(wizard, [{
            'company_id': self.env.company.id,
            'parent_company_id': self.env.company.id,
            'selected_company_id': self.env.company.id,
            'use_parent_connection_selection': 'use_self',
        }])
        with self._mock_requests([
            self._mock_create_user(),
            self._mock_lookup_participant(already_exist=True),
            self._mock_register_sender(),
        ]):
            wizard.button_register_peppol_participant()

        settings = self.env['res.config.settings'].with_context(allowed_company_ids=self.env.company.ids).create({})
        self.assertRecordValues(settings, [{
            'account_peppol_proxy_state': 'sender',
            'peppol_use_parent_company': False,
        }])

        # Back to the branch.
        wizard = self.env['peppol.registration'].with_context(allowed_company_ids=branch.ids).create({})
        self.assertRecordValues(wizard, [{
            'company_id': branch.id,
            'parent_company_id': self.env.company.id,
            'selected_company_id': branch.id,
            'use_parent_connection_selection': 'use_self',
        }])
        wizard.write({
            'contact_email': "turlututu@tsointsoin",
            'phone_number': "+3236656565",
            'peppol_eas': '0208',
            'peppol_endpoint': '0239843188',
        })
        self.assertRecordValues(wizard, [{
            'company_id': branch.id,
            'parent_company_id': self.env.company.id,
            'selected_company_id': self.env.company.id,
            'use_parent_connection_selection': 'use_parent',
        }])
        with self._mock_requests([
            self._mock_create_user(),
            self._mock_lookup_participant(already_exist=True),
            self._mock_register_sender(),
        ]):
            wizard.button_register_peppol_participant()
        self.assertRecordValues(branch, [{
            'peppol_parent_company_id': self.env.company.id,
            'peppol_eas': '0208',
            'peppol_endpoint': '0239843188',
        }])

        settings = self.env['res.config.settings'].with_context(allowed_company_ids=branch.ids).create({})
        self.assertRecordValues(settings, [{
            'account_peppol_proxy_state': 'sender',
            'peppol_use_parent_company': True,
        }])

        # Disconnect from the network.
        with self._mock_requests([
            self._mock_cancel_peppol_registration(),
            self._mock_participant_status('sender'),
        ]):
            settings.button_deregister_peppol_participant()
        self.assertRecordValues(settings, [{
            'account_peppol_proxy_state': 'not_registered',
            'peppol_use_parent_company': False,
        }])

        # Back to the initial state.
        wizard = self.env['peppol.registration'].with_context(allowed_company_ids=branch.ids).create({})
        self.assertRecordValues(wizard, [{
            'company_id': branch.id,
            'parent_company_id': self.env.company.id,
            'selected_company_id': branch.id,
            'use_parent_connection_selection': 'use_self',
            'peppol_eas': False,
            'peppol_endpoint': False,
            'phone_number': False,
            'contact_email': False,
        }])

    def test_deregister_with_client_gone_error(self):
        """Test deregistration succeeds even when proxy returns client_gone error"""
<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
        with self._mock_requests([
            self._mock_create_user(),
            self._mock_lookup_participant(),
            self._mock_register_sender(),
        ]):
            wizard = self.env['peppol.registration'].create({})
            self.assertRecordValues(wizard, [{'smp_registration': True}])
            wizard.button_register_peppol_participant()
        with self._mock_requests([self._mock_participant_status('sender')]):
            self.env.company.account_edi_proxy_client_ids._peppol_get_participant_status()
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'sender')
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'active')
=======
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_register_with_kyc()
        self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'active')
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

        settings = self.env['res.config.settings'].create({})
        with self._mock_requests([
            self._mock_participant_status('sender', exists=False)
        ]):
            settings.button_deregister_peppol_participant()

        # Should successfully deregister despite Exception
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'not_registered')

    def test_peppol_commercial_entity(self):
        receivable = self.env["account.account"].create({
            "account_type": "income",
            "name": "test_receiv",
            "code": "TESTR"
        })
        payable = self.env["account.account"].create({
            "account_type": "expense",
            "name": "test_pay",
            "code": "TESTP"
        })
        company_peppol = self.env["res.company"].create({
            "name": "test_be",
            "country_id": self.env.ref("base.be").id,
        })
        partner_view = self.env.ref("base.view_partner_form")
        self.env["ir.ui.view"].create({
            "name": "test_inherit",
            "inherit_id": partner_view.id,
            "model": "res.partner",
            "type": "form",
            "arch": """<xpath expr="//field" position="after">
                    <field name="commercial_partner_id" />
                </xpath>"""
        })
        env_partner = (self.env["res.partner"]
            .with_company(company_peppol)
            .with_context(
                default_property_account_receivable_id=receivable.id,
                default_property_account_payable_id=payable.id
            ))
        with Form(env_partner, view=partner_view) as partner_form:
            self.assertEqual(partner_form.peppol_verification_state, "not_verified")
            partner_form.name = "test"
            partner_form.vat = "BE0477472701"
            partner_form.peppol_eas = "odemo"
            self.assertFalse(partner_form.commercial_partner_id)
            p_rec = partner_form.save()
            self.assertEqual(partner_form.peppol_verification_state, "not_valid")
            self.assertEqual(p_rec.commercial_partner_id, p_rec)
            self.assertEqual(p_rec.commercial_partner_id.name, "test")

    def test_do_not_reset_peppol_endpoint(self):
        be_country = self.env.ref('base.be')
        self.env.company.write({
            'country_id': be_country.id,
            'vat': 'BE0477472701',
        })
<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
        with self._mock_requests([
            self._mock_create_user(),
            self._mock_lookup_participant(),
            self._mock_register_sender(),
        ]):
            wizard = self.env['peppol.registration'].create({
                'peppol_eas': '0088',
                'peppol_endpoint': '88888888888',
                'phone_number': '+32483123456',
                'contact_email': 'yourcompany@test.example.com',
            })
            wizard.button_register_peppol_participant()
        with self._mock_requests([self._mock_participant_status('sender')]):
            self.env.company.account_edi_proxy_client_ids._peppol_get_participant_status()
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
        settings = self.env['res.config.settings'].create({
            'account_peppol_eas': '0088',
            'account_peppol_endpoint': '88888888888',
            'account_peppol_phone_number': '+32483123456',
            'account_peppol_contact_email': 'yourcompany@test.example.com',
        })
        settings.button_create_peppol_proxy_user()
        self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
=======
        settings = self.env['res.config.settings'].create({
            'account_peppol_eas': '0088',
            'account_peppol_endpoint': '88888888888',
            'account_peppol_phone_number': '+32483123456',
            'account_peppol_contact_email': 'yourcompany@test.example.com',
        })
        settings.button_register_with_kyc()
        self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a
        self.env.company.vat = 'BE0475646428'
        self.assertRecordValues(self.env.company.partner_id, [{
            'peppol_eas': '0088',
            'peppol_endpoint': '88888888888',
        }])

        with Form(self.env.company.partner_id) as partner:
            # Test with NewID record
            partner.vat = 'BE0477472701'
        self.assertRecordValues(self.env.company.partner_id, [{
            'peppol_eas': '0088',
            'peppol_endpoint': '88888888888',
        }])

        company_partner = self.env.company.partner_id

        other_company = self.env['res.company'].create({'name': 'new company 3', 'country_id': be_country.id})
        self.env = self.env(context=dict(allowed_company_ids=other_company.ids))
        # Do not raise even if no access to a registered company

        company_partner.vat = 'BE0477472701'
        self.assertRecordValues(company_partner, [{
            'peppol_eas': '0088',
            'peppol_endpoint': '88888888888',
        }])

        self.env.company.vat = 'BE0475646428'
        self.assertRecordValues(self.env.company.partner_id, [{
            'peppol_eas': '0208',
            'peppol_endpoint': '0475646428',
        }])
<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
||||||| 89081cc015d517880d3cadc2d61c278b4b379502

    def test_create_child_company_sender_only(self):
        """Test that when a child company attempts to register on Peppol using the exact same endpoint as its already active parent company"""
        vals = self._get_participant_vals()
        parent_company = self.env['res.company'].create({
            'name': 'Parent Company',
            'peppol_eas': vals['account_peppol_eas'],
            'peppol_endpoint': vals['account_peppol_endpoint'],
        })

        child_company = self.env['res.company'].create({
            'name': 'Child Company Connection',
            'parent_id': parent_company.id,
            'peppol_eas': vals['account_peppol_eas'],
            'peppol_endpoint': vals['account_peppol_endpoint'],
        })

        self.env['account_edi_proxy_client.user'].sudo().create({
            'id_client': 'parent_client',
            'company_id': parent_company.id,
            'proxy_type': 'peppol',
            'edi_mode': 'test',
            'edi_identification': f"{vals['account_peppol_eas']}:{vals['account_peppol_endpoint']}",
            'refresh_token': FAKE_UUID,
            'private_key': '1234',
        })

        settings = self.env['res.config.settings'].with_company(child_company).create(vals)
        settings.button_create_peppol_proxy_user()

        self.assertEqual(child_company.account_peppol_proxy_state, 'sender')
        self.assertTrue(settings.peppol_use_parent_company)

        child_user = self.env['account_edi_proxy_client.user'].search([
            ('company_id', '=', child_company.id),
            ('proxy_type', '=', 'peppol'),
        ])
        self.assertEqual(child_user.edi_identification, f"{vals['account_peppol_eas']}:{vals['account_peppol_endpoint']}")
=======

    def test_create_child_company_sender_only(self):
        """Test that when a child company attempts to register on Peppol using the exact same endpoint as its already active parent company"""
        vals = self._get_participant_vals()
        parent_company = self.env['res.company'].create({
            'name': 'Parent Company',
            'peppol_eas': vals['account_peppol_eas'],
            'peppol_endpoint': vals['account_peppol_endpoint'],
        })

        child_company = self.env['res.company'].create({
            'name': 'Child Company Connection',
            'parent_id': parent_company.id,
            'peppol_eas': vals['account_peppol_eas'],
            'peppol_endpoint': vals['account_peppol_endpoint'],
        })

        self.env['account_edi_proxy_client.user'].sudo().create({
            'id_client': 'parent_client',
            'company_id': parent_company.id,
            'proxy_type': 'peppol',
            'edi_mode': 'test',
            'edi_identification': f"{vals['account_peppol_eas']}:{vals['account_peppol_endpoint']}",
            'refresh_token': FAKE_UUID,
            'private_key': '1234',
        })

        settings = self.env['res.config.settings'].with_company(child_company).create(vals)
        with self._set_context({'connect_state': 'sender'}):
            settings.button_register_with_kyc()

        self.assertEqual(child_company.account_peppol_proxy_state, 'sender')
        self.assertTrue(settings.peppol_use_parent_company)

        child_user = self.env['account_edi_proxy_client.user'].search([
            ('company_id', '=', child_company.id),
            ('proxy_type', '=', 'peppol'),
        ])
        self.assertEqual(child_user.edi_identification, f"{vals['account_peppol_eas']}:{vals['account_peppol_endpoint']}")
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a
