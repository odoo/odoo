from contextlib import contextmanager
from requests import PreparedRequest, Response, Session

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

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
            '/api/pdp/1/participant_status': {
                'result': {
                    'pdp_state': participant_state,
                }
            },
            '/api/pdp/1/cancel_pdp_registration': {'result': {}},
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
            'pdp_identifier': '0000000000',
            'phone_number': '+32483123456',
            'contact_email': 'yourcompany@test.example.com',
        }

    @contextmanager
    def _set_context(self, other_context):
        previous_context = self.env.context
        self.env.context = dict(previous_context, **other_context)
        yield self
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
        self.assertEqual(company.l10n_fr_pdp_proxy_state, 'pending')

        # The participant should be automatically registered as receiver after some time
        with self._set_context({'participant_state': 'receiver'}):
            self.env['account_edi_proxy_client.user']._cron_pdp_get_participant_status()
            self.assertEqual(self.env.company.l10n_fr_pdp_proxy_state, 'receiver')

    def test_pdp_create_reject_participant(self):
        # the l10n_fr_pdp_proxy_state should change to rejected
        # if we reject the participant
        company = self.env.company
        wizard = self.env['pdp.registration'].create(self._get_participant_vals())

        with self._set_context({'participant_state': 'rejected'}):
            wizard.button_register_pdp_participant()
            self.env['account_edi_proxy_client.user']._cron_pdp_get_participant_status()
            self.assertEqual(company.l10n_fr_pdp_proxy_state, 'rejected')

    def test_pdp_create_duplicate_participant(self):
        """ If you create a duplicate participant, it will take over the previous one"""
        wizard = self.env['pdp.registration'].create(self._get_participant_vals())
        wizard.button_register_pdp_participant()

        wizard.l10n_fr_pdp_proxy_state = False
        wizard.button_register_pdp_participant()
        self.assertEqual(self.env.company.l10n_fr_pdp_proxy_state, 'pending')

        # The participant is still a receiver on IAP
        with self._set_context({'participant_state': 'receiver'}):
            self.env['account_edi_proxy_client.user']._cron_pdp_get_participant_status()
            self.assertEqual(self.env.company.l10n_fr_pdp_proxy_state, 'receiver')
