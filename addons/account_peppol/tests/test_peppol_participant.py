# -*- coding: utf-8 -*

from contextlib import contextmanager
from freezegun import freeze_time
from unittest.mock import Mock, patch
from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import tagged, TransactionCase
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

    def _get_participant_vals(self):
        return {
            'account_peppol_eas': '9925',
            'account_peppol_endpoint': '0000000000',
            'account_peppol_phone_number': '+32483123456',
            'account_peppol_contact_email': 'yourcompany@test.example.com',
        }

    @contextmanager
    def _patch_peppol_requests(self, reject=False, migrate_to=False, migrated_away=False):
        responses = {
            '/peppol/1/participant_status': {
                'result': {
                    'peppol_state': 'active' if not reject else 'rejected',
                }
            },
            '/peppol/1/activate_participant': {'result': {}},
            '/account_edi/2/create_user': {
                'result': {
                    'id_client': ID_CLIENT,
                    'refresh_token': FAKE_UUID,
                }
            },
            '/peppol/1/send_verification_code': {'result': {}},
            '/peppol/1/update_user': {'result': {}},
            '/peppol/1/verify_phone_number': {'result': {}},
            '/peppol/1/migrate_peppol_registration': {
                'result': {
                    'migration_key': 'test_key',
                }
            },
        }

        def _mocked_post(url, *args, **kwargs):
            response = Mock()
            response.status_code = 200
            if (
                url.endswith('/api/peppol/1/activate_participant')
                and migrate_to
                and not kwargs['json']['params']['migration_key']
            ):
                raise UserError('No migration key was provided')

            if migrated_away:
                response.json = lambda: {
                    'result': {
                        'proxy_error': {
                            'code': 'no_such_user',
                            'message': 'The user does not exist on the proxy',
                        }
                    }
                }
                return response

            url = url.split('/api')[1] if 'iap' not in url else url.split('/iap')[1]
            if url not in responses:
                raise Exception(f'Unexpected request: {url}')
            response.json = lambda: responses[url]

            return response

        with patch('odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user.requests.post', side_effect=_mocked_post):
            yield

    def test_create_participant_missing_data(self):
        # creating a participant without eas/endpoint/document should not be possible
        settings = self.env['res.config.settings'].create({
            'account_peppol_eas': False,
            'account_peppol_endpoint': False,
        })
        with self.assertRaises(ValidationError), self.cr.savepoint():
            settings.button_create_peppol_proxy_user()

    def test_create_success_participant(self):
        # should be possible to apply with all data
        # the account_peppol_proxy_state should correctly change to pending
        # then the account_peppol_proxy_state should change success
        # after checking participant status
        company = self.env.company
        settings = self.env['res.config.settings'].create(self._get_participant_vals())

        with self._patch_peppol_requests():
            settings.button_create_peppol_proxy_user()
            self.assertEqual(company.account_peppol_proxy_state, 'not_verified')
            settings.button_send_peppol_verification_code()
            self.assertEqual(company.account_peppol_proxy_state, 'sent_verification')
            settings.account_peppol_verification_code = '123456'
            settings.button_check_peppol_verification_code()
            self.assertEqual(company.account_peppol_proxy_state, 'pending')
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(company.account_peppol_proxy_state, 'active')

    def test_create_reject_participant(self):
        # the account_peppol_proxy_state should change to rejected
        # if we reject the participant
        company = self.env.company
        settings = self.env['res.config.settings'].create(self._get_participant_vals())

        with self._patch_peppol_requests(reject=True):
            settings.button_create_peppol_proxy_user()
            company.account_peppol_proxy_state = 'pending'
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(company.account_peppol_proxy_state, 'rejected')

    @mute_logger('odoo.sql_db')
    def test_create_duplicate_participant(self):
        # should not be possible to create a duplicate participant
        settings = self.env['res.config.settings'].create(self._get_participant_vals())

        with self._patch_peppol_requests():
            settings.button_create_peppol_proxy_user()
            with self.assertRaises(IntegrityError), self.cr.savepoint():
                settings.account_peppol_proxy_state = 'not_registered'
                settings.button_create_peppol_proxy_user()

    def test_save_migration_key(self):
        # migration key should be saved
        settings = self.env['res.config.settings']\
            .create({
                **self._get_participant_vals(),
                'account_peppol_migration_key': 'helloo',
            })

        with self._patch_peppol_requests(migrate_to=True):
            settings.button_create_peppol_proxy_user()
            self.assertEqual(self.env.company.account_peppol_proxy_state, 'not_verified')
            self.assertFalse(settings.account_peppol_migration_key) # the key should be reset once we've used it

    def test_migrate_away_participant(self):
        # a participant should be able to request a migration key
        settings = self.env['res.config.settings'].create(self._get_participant_vals())

        with self._patch_peppol_requests():
            self.assertFalse(settings.account_peppol_migration_key)
            settings.button_create_peppol_proxy_user()
            settings.account_peppol_proxy_state = 'active'
            settings.button_migrate_peppol_registration()
            self.assertEqual(self.env.company.account_peppol_proxy_state, 'active')
            self.assertEqual(settings.account_peppol_migration_key, 'test_key')

    def test_reset_participant(self):
        # once a participant has migrated away, they should be reset
        settings = self.env['res.config.settings'].create(self._get_participant_vals())

        with self._patch_peppol_requests():
            settings.button_create_peppol_proxy_user()
            settings.account_peppol_proxy_state = 'active'
            settings.button_migrate_peppol_registration()

        with self._patch_peppol_requests(migrated_away=True):
            try:
                settings.button_update_peppol_user_data()
            except UserError:
                settings = self.env['res.config.settings'].create({})
                self.assertRecordValues(
                    settings, [{
                        'account_peppol_migration_key': False,
                        'account_peppol_proxy_state': 'not_registered',
                    }]
                )
                self.assertFalse(self.env.company.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol'))
            else:
                raise ValidationError('A UserError should be raised.')
