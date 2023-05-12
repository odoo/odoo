# -*- coding: utf-8 -*

from contextlib import contextmanager
from freezegun import freeze_time
from unittest.mock import Mock, patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged, TransactionCase
from odoo.tools import file_open

ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
FAKE_UUID = 'yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy'
PDF_FILE_PATH = 'account_peppol/tests/assets/peppol_identification_test.pdf'


@freeze_time('2023-01-01')
@tagged('-at_install', 'post_install')
class TestPeppolParticipant(TransactionCase):

    @contextmanager
    def _patch_peppol_requests(self, reject=False):
        def _mocked_post(url, *args, **kwargs):
            response = Mock()
            response.status_code = 200
            if url.endswith('api/peppol/1/participant_status'):
                response.json = lambda: {'result': {
                    'peppol_state': 'active' if not reject else 'rejected',
                }}
            elif url.endswith('/api/peppol/1/activate_participant'):
                response.json = lambda: {'result': {}}
            elif url.endswith('/iap/account_edi/2/create_user'):
                response.json = lambda: {'result': {
                    'id_client': ID_CLIENT, 'refresh_token': FAKE_UUID}}
            else:
                raise Exception(f'Unexpected request: {url}')

            return response

        with patch('odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user.requests.post', side_effect=_mocked_post):
            yield

    def test_create_participant_missing_data(self):
        # creating a participant without eas/endpoint/document should not be possible
        settings = self.env['res.config.settings'].create({})
        settings.write({
            'is_account_peppol_participant': True,
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
        settings = self.env['res.config.settings'].create({})
        settings.write({
            'is_account_peppol_participant': True,
            'account_peppol_eas': '9925',
            'account_peppol_endpoint': '0000000000',
        })
        company = self.env.company

        with file_open(PDF_FILE_PATH, 'rb') as pdf_file:
            settings.account_peppol_attachment_ids = self.env['ir.attachment'].create({
                'mimetype': 'application/pdf',
                'name': 'peppol_id_test.pdf',
                'raw': pdf_file.read(),
            }).ids

        settings.execute()

        with self._patch_peppol_requests():
            settings.button_create_peppol_proxy_user()
            self.assertEqual(company.account_peppol_proxy_state, 'pending')
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(company.account_peppol_proxy_state, 'active')

    def test_create_reject_participant(self):
        # the account_peppol_proxy_state should change to rejected
        # if we reject the participant
        settings = self.env['res.config.settings'].create({})
        settings.write({
            'is_account_peppol_participant': True,
            'account_peppol_eas': '9925',
            'account_peppol_endpoint': '0000000000',
        })
        company = self.env.company

        with file_open(PDF_FILE_PATH, 'rb') as pdf_file:
            settings.account_peppol_attachment_ids = self.env['ir.attachment'].create({
                'mimetype': 'application/pdf',
                'name': 'peppol_id_test.pdf',
                'raw': pdf_file.read(),
            }).ids

        settings.execute()

        with self._patch_peppol_requests(reject=True):
            settings.button_create_peppol_proxy_user()
            self.assertEqual(company.account_peppol_proxy_state, 'pending')
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(company.account_peppol_proxy_state, 'rejected')

    def test_create_duplicate_participant(self):
        # should not be possible to create a duplicate participant
        settings = self.env['res.config.settings'].create({})
        settings.write({
            'is_account_peppol_participant': True,
            'account_peppol_eas': '9925',
            'account_peppol_endpoint': '0000000000',
        })

        with file_open(PDF_FILE_PATH, 'rb') as pdf_file:
            settings.account_peppol_attachment_ids = self.env['ir.attachment'].create({
                'mimetype': 'application/pdf',
                'name': 'peppol_id_test.pdf',
                'raw': pdf_file.read(),
            }).ids

        settings.execute()

        with self._patch_peppol_requests():
            settings.button_create_peppol_proxy_user()
            self.assertEqual(settings.account_peppol_proxy_state, 'pending')
            with self.assertRaises(UserError), self.cr.savepoint():
                settings.button_create_peppol_proxy_user()
