from contextlib import contextmanager
from requests import PreparedRequest, Response, Session
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged, TransactionCase, freeze_time

ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
FAKE_UUID = 'yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy'


@freeze_time('2023-01-01')
@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestNemhandelParticipant(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('l10n_dk_nemhandel.edi.mode', 'test')
        cls.env.company.vat = 'DK12345674'

    @classmethod
    def _get_mock_responses(cls):
        participant_state = cls.env.context.get('participant_state', 'receiver')
        return {
            '/api/nemhandel/1/participant_status': {
                'result': {
                    'nemhandel_state': participant_state,
                }
            },
            '/api/nemhandel/1/register_participant': {'result': {}},
            '/api/nemhandel/1/connect': {
                'result': {
                    'id_client': ID_CLIENT,
                    'refresh_token': FAKE_UUID,
                }
            },
            '/api/nemhandel/1/cancel_nemhandel_registration': {'result': {}},
            '/api/nemhandel/1/update_user': {'result': {}},
            '/api/nemhandel/1/verify_phone_number': {'result': {}},
            '/api/nemhandel/1/send_verification_code': {'result': {}},
            '/api/nemhandel/1/check_user_valid': {'result': {'status': 'valid'}}
        }

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        response = Response()
        response.status_code = 200
        if r.url.endswith('/iso6523-actorid-upis%3A%3A0088%3A0000000000'):
            response.status_code = 404
            return response

        if r.url.endswith('/iso6523-actorid-upis%3A%3A0184%3A0000000000'):
            response._content = b'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<smp:ServiceGroup xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:id="http://busdox.org/transport/identifiers/1.0/" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:smp="http://busdox.org/serviceMetadata/publishing/1.0/"><id:ParticipantIdentifier scheme="iso6523-actorid-upis">0184:0000000000</id:ParticipantIdentifier></smp:ServiceGroup>'
            return response

        url = r.path_url
        responses = cls._get_mock_responses()

        if url not in responses:
            return super()._request_handler(s, r, **kw)
        response.json = lambda: responses[url]
        return response

    def _get_participant_vals(self):
        return {
            'identifier_type': '0088',
            'identifier_value': '0000000000',
            'phone_number': '+32483123456',
            'contact_email': 'yourcompany@test.example.com',
        }

    @contextmanager
    def _set_context(self, other_context):
        cls = self.__class__
        env = cls.env(context=dict(cls.env.context, **other_context))
        with patch.object(cls, "env", env):
            yield

    def test_nemhandel_create_participant_missing_data(self):
        # creating a participant without identifier should not be possible
        wizard = self.env['nemhandel.registration'].create({
            'identifier_type': False,
            'identifier_value': False,
        })
        with self.assertRaises(ValidationError), self.cr.savepoint():
            wizard.button_nemhandel_registration_sms()

    def test_nemhandel_create_participant_receiver(self):
        company = self.env.company
        wizard = self.env['nemhandel.registration'].create(self._get_participant_vals())
        wizard.button_nemhandel_registration_sms()
        self.assertEqual(company.l10n_dk_nemhandel_proxy_state, 'in_verification')
        wizard.verification_code = '888888'
        wizard.button_nemhandel_receiver_registration()
        self.assertEqual(company.l10n_dk_nemhandel_proxy_state, 'receiver')

    def test_nemhandel_create_reject_participant(self):
        # the l10n_dk_nemhandel_proxy_state should change to rejected
        # if we reject the participant
        company = self.env.company
        wizard = self.env['nemhandel.registration'].create(self._get_participant_vals())

        with self._set_context({'participant_state': 'rejected'}):
            wizard.button_nemhandel_registration_sms()
            self.env['account_edi_proxy_client.user']._cron_nemhandel_get_participant_status()
            self.assertEqual(company.l10n_dk_nemhandel_proxy_state, 'rejected')

    def test_nemhandel_create_duplicate_participant(self):
        """ If you create a duplicate participant, it will take over the previous one"""
        wizard = self.env['nemhandel.registration'].create(self._get_participant_vals())
        wizard.button_nemhandel_registration_sms()
        wizard.verification_code = '888888'
        wizard.button_nemhandel_receiver_registration()
        wizard.l10n_dk_nemhandel_proxy_state = 'not_registered'
        wizard.button_nemhandel_registration_sms()
        self.assertEqual(self.env.company.l10n_dk_nemhandel_proxy_state, 'in_verification')

        # The participant is still a receiver on IAP
        with self._set_context({'participant_state': 'receiver'}):
            self.env['account_edi_proxy_client.user']._cron_nemhandel_get_participant_status()
            self.assertEqual(self.env.company.l10n_dk_nemhandel_proxy_state, 'receiver')
