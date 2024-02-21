import json
from contextlib import contextmanager
from freezegun import freeze_time
from requests import Session, PreparedRequest, Response
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

    @classmethod
    def _get_mock_responses(cls, reject=False):
        return {
            '/api/peppol/1/participant_status': {
                'result': {
                    'peppol_state': 'active' if not reject else 'rejected',
                }
            },
            '/api/peppol/1/activate_participant': {'result': {}},
            '/iap/account_edi/2/create_user': {
                'result': {
                    'id_client': ID_CLIENT,
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
        }

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        response = Response()
        response.status_code = 200
        if r.url.endswith('/iso6523-actorid-upis%3A%3A9925%3A0000000000'):
            response.status_code = 404
            return response

        if r.url.endswith('/iso6523-actorid-upis%3A%3A0208%3A0000000000'):
            response._content = b'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<smp:ServiceGroup xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:id="http://busdox.org/transport/identifiers/1.0/" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:smp="http://busdox.org/serviceMetadata/publishing/1.0/"><id:ParticipantIdentifier scheme="iso6523-actorid-upis">0208:0000000000</id:ParticipantIdentifier></smp:ServiceGroup>'
            return response

        url = r.path_url
        body = json.loads(r.body)
        responses = cls._get_mock_responses(cls.env.context.get('reject'))
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

        with self._set_context({'reject': True}):
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

    def test_save_migration_key(self):
        # migration key should be saved
        settings = self.env['res.config.settings']\
            .create({
                **self._get_participant_vals(),
                'account_peppol_migration_key': 'helloo',
            })

        with self._set_context({'migrate_to': True}):
            settings.button_create_peppol_proxy_user()
            self.assertEqual(self.env.company.account_peppol_proxy_state, 'not_verified')
            self.assertFalse(settings.account_peppol_migration_key) # the key should be reset once we've used it

    def test_migrate_away_participant(self):
        # a participant should be able to request a migration key
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        self.assertFalse(settings.account_peppol_migration_key)
        settings.button_create_peppol_proxy_user()
        settings.account_peppol_proxy_state = 'active'
        settings.button_migrate_peppol_registration()
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'active')
        self.assertEqual(settings.account_peppol_migration_key, 'test_key')

    def test_reset_participant(self):
        # once a participant has migrated away, they should be reset
        settings = self.env['res.config.settings'].create(self._get_participant_vals())
        settings.button_create_peppol_proxy_user()
        settings.account_peppol_proxy_state = 'active'
        settings.button_migrate_peppol_registration()

        with self._set_context({'migrated_away': True}):
            try:
                settings.button_update_peppol_user_data()
            except UserError:
                settings = self.env['res.config.settings'].create({})
                self.assertRecordValues(settings, [{
                        'account_peppol_migration_key': False,
                        'account_peppol_proxy_state': 'not_registered',
                    }],
                )
                self.assertFalse(self.env.company.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol'))
            else:
                raise ValidationError('A UserError should be raised.')
