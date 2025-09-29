import datetime
import requests
from contextlib import contextmanager
from freezegun import freeze_time
from psycopg2 import IntegrityError
from requests import Session, PreparedRequest, Response
from unittest.mock import patch
from urllib.parse import parse_qs, quote_plus

from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import tagged, TransactionCase
from odoo.tools import mute_logger

ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
FAKE_UUID = 'yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy'
PDF_FILE_PATH = 'account_peppol/tests/assets/peppol_identification_test.pdf'

# SMP returns 200 for these and 404 otherwise
SMP_OK_IDS = {'0208:0000000000', '0208:0000000001'}


@tagged('-at_install', 'post_install')
class TestPeppolParticipant(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fakenow = datetime.datetime(2023, 1, 1, 12, 20, 0)
        cls.startClassPatcher(freeze_time(cls.fakenow))
        cls.env['ir.config_parameter'].sudo().set_param('account_edi_proxy_client.demo', 'test')

        patcher = patch.object(
            requests.sessions.Session,
            'send',
            lambda s, r, **kwargs: cls._request_handler(s, r, **kwargs),  # noqa: PLW0108
        )
        cls.startClassPatcher(patcher)

    @classmethod
    def _get_mock_responses(cls, peppol_state='active'):
        return {
            '/api/peppol/1/participant_status': {
                'result': {
                    'peppol_state': peppol_state,
                }
            },
            '/api/peppol/1/activate_participant': {'result': {}},
            '/iap/account_edi/2/create_user': {
                'result': {
                    'id_client': cls.env.context.get('mock_id_client', ID_CLIENT),
                    'refresh_token': FAKE_UUID,
                }
            },
            '/api/peppol/1/send_verification_code': {'result': {}},
            '/api/peppol/1/update_user': {'result': {}},
            '/api/peppol/1/verify_phone_number': {'result': {}},
            '/api/peppol/1/register_receiver': {'result': {}},
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

        custom_responses_by_id = cls.env.context.get('custom_responses_by_id')
        if custom_responses_by_id:
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
            raise NotImplementedError
        response.json = lambda: responses[url]
        return response

    def _get_participant_vals(self):
        return {
            'account_peppol_eas': '9925',
            'account_peppol_endpoint': '0000000000',
            'account_peppol_phone_number': '+32483123456',
            'account_peppol_contact_email': 'yourcompany@test.example.com',
        }

    @contextmanager
    def _set_context(self, other_context):
        previous_context = self.env.context
        self.env.context = dict(previous_context, **other_context)
        yield self
        self.env.context = previous_context

    def test_create_participant_missing_data(self):
        # creating a participant without eas/endpoint/document should not be possible
        settings = self.env['res.config.settings'].create({
            'account_peppol_eas': False,
            'account_peppol_endpoint': False,
        })
        with self.assertRaises(ValidationError), self.cr.savepoint():
            settings.button_create_peppol_proxy_user()

    def test_create_participant_already_exists(self):
        # creating a participant that already exists on Peppol network should not be possible
        vals = self._get_participant_vals()
        vals['account_peppol_eas'] = '0208'
        settings = self.env['res.config.settings'].create(vals)
        with self.assertRaises(UserError), self.cr.savepoint():
            settings.button_create_peppol_proxy_user()

    def test_create_success_participant(self):
        # should be possible to apply with all data
        # the account_peppol_proxy_state should correctly change to pending
        # then the account_peppol_proxy_state should change success
        # after checking participant status
        company = self.env.company
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        self.assertEqual(company.account_peppol_proxy_state, 'pending')
        self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
        self.assertEqual(company.account_peppol_proxy_state, 'active')

    def test_create_reject_participant(self):
        # the account_peppol_proxy_state should change to rejected
        # if we reject the participant
        company = self.env.company
        settings = self.env['res.config.settings'].create(self._get_participant_vals())

        with self._set_context({'peppol_state': 'rejected'}):
            settings.button_create_peppol_proxy_user()
            company.account_peppol_proxy_state = 'pending'
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(company.account_peppol_proxy_state, 'rejected')

    @mute_logger('odoo.sql_db')
    def test_create_duplicate_participant(self):
        # should not be possible to create a duplicate participant
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            settings.account_peppol_proxy_state = 'not_registered'
            settings.button_create_peppol_proxy_user()

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
        """Test recovery when IAP-side is in KYC state (should set to `pending` and not keep in `not_registered`)"""
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        edi_user = self.env.company.account_edi_proxy_client_ids

        # simulate soft-delete
        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        # mock IAP returning draft state (thus still in KYC)
        with self._set_context({'peppol_state': 'draft'}):
            result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(edi_user.company_id)

        # should recover user and set state to 'pending'
        self.assertEqual(result, edi_user)
        self.assertTrue(edi_user.active)
        self.assertEqual(edi_user.company_id.account_peppol_proxy_state, 'pending')

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
        self.env['ir.config_parameter'].sudo().set_param('account_edi_proxy_client.demo', 'demo')

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

    def test_recovery_company_inconsistent_state_skip(self):
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        edi_user = self.env.company.account_edi_proxy_client_ids

        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'pending'

        result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(edi_user.company_id)

        # Should not recover when company state is not 'not_registered'
        self.assertIsNone(result)
        self.assertFalse(edi_user.active)

    def test_recovery_malformed_response_handling(self):
        """Test recovery handles malformed API responses"""
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        with self._set_context({'mock_id_client': 'error-client-id'}):
            settings.button_create_peppol_proxy_user()
        edi_user = self.env.company.account_edi_proxy_client_ids

        edi_user.active = False
        edi_user.company_id.account_peppol_proxy_state = 'not_registered'

        with self._set_context({'custom_responses_by_id': {
            'error-client-id': {'result': {'some_key': 'some_value'}}
        }}):
            result = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(edi_user.company_id)

            # handle malformed response gracefully
            self.assertIsNone(result)
            self.assertFalse(edi_user.active)
