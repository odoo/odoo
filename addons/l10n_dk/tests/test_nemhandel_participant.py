from odoo.exceptions import ValidationError
from odoo.tests.common import tagged, TransactionCase, freeze_time

from odoo.addons.l10n_dk.tests.common import mock_nemhandel_registration, mock_nemhandel_smp

# SMP ServiceGroup served for a registered participant
SERVICE_GROUP_XML = (
    b'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n'
    b'<smp:ServiceGroup xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:id="http://busdox.org/transport/identifiers/1.0/"'
    b' xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:smp="http://busdox.org/serviceMetadata/publishing/1.0/">'
    b'<id:ParticipantIdentifier scheme="iso6523-actorid-upis">0184:0000000000</id:ParticipantIdentifier></smp:ServiceGroup>'
)


@freeze_time('2023-01-01')
@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestNemhandelParticipant(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_str('l10n_dk.edi.mode', 'test')
        cls.env.company.vat = 'DK12345674'

    def _get_participant_vals(self):
        return {
            'identifier_type': '0088',
            'identifier_value': '0000000000',
            'phone_number': '+32483123456',
            'contact_email': 'yourcompany@test.example.com',
        }

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
        with (
            mock_nemhandel_registration(),
            mock_nemhandel_smp({'0088:0000000000': None, '0184:0000000000': SERVICE_GROUP_XML}),
        ):
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
        with (
            mock_nemhandel_registration(nemhandel_state='rejected'),
            mock_nemhandel_smp({'0088:0000000000': None, '0184:0000000000': SERVICE_GROUP_XML}),
        ):
            wizard = self.env['nemhandel.registration'].create(self._get_participant_vals())
            wizard.button_nemhandel_registration_sms()
            self.env['account_edi_proxy_client.user']._cron_nemhandel_get_participant_status()
            self.assertEqual(company.l10n_dk_nemhandel_proxy_state, 'rejected')

    def test_nemhandel_create_duplicate_participant(self):
        """ If you create a duplicate participant, it will take over the previous one"""
        with (
            mock_nemhandel_registration(),
            mock_nemhandel_smp({'0088:0000000000': None, '0184:0000000000': SERVICE_GROUP_XML}),
        ):
            wizard = self.env['nemhandel.registration'].create(self._get_participant_vals())
            wizard.button_nemhandel_registration_sms()
            wizard.verification_code = '888888'
            wizard.button_nemhandel_receiver_registration()
            wizard.l10n_dk_nemhandel_proxy_state = 'not_registered'
            wizard.button_nemhandel_registration_sms()
            self.assertEqual(self.env.company.l10n_dk_nemhandel_proxy_state, 'in_verification')

            # The participant is still a receiver on IAP
            self.env['account_edi_proxy_client.user']._cron_nemhandel_get_participant_status()
            self.assertEqual(self.env.company.l10n_dk_nemhandel_proxy_state, 'receiver')
