from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .common import TestL10nFrPdpCommon, mock_pdp_registration


@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestPdpUser(TestL10nFrPdpCommon):

    def _get_participant_vals(self):
        return {
            'pdp_identifier': '000000000',
            'contact_email': 'yourcompany@test.example.com',
        }

    def test_pdp_create_participant_missing_siren(self):
        self.env.company.partner_id.write({
            'routing_identifier': '0002:552008443',
            'additional_identifiers': {},
        })
        self.assertFalse(self.env.company.partner_id._l10n_fr_pdp_get_siren())
        wizard = self.env['pdp.registration'].create({'contact_email': "test@pdp.example.com"})
        # we can not suggest a pdp identifier; we display a warning instead
        self.assertFalse(wizard.pdp_identifier)
        self.assertTrue(wizard.warnings['company_siren_warning'])
        with self.assertRaisesRegex(UserError, "The Identifier is required."):
            wizard.button_register_pdp_participant()

    def test_pdp_create_participant_missing_pdp_identifier(self):
        # When the company does not have a 0225 peppol EAS set we should still suggest
        # an identifier in the wizard.
        self.env.company.partner_id.write({
            'routing_identifier': '0002:944716448',
            'additional_identifiers': {'FR_SIREN': '944716448'},
        })
        self.assertFalse(self.env.company.pdp_identifier)
        wizard = self.env['pdp.registration'].create({'contact_email': 'yourcompany@test.example.com'})
        self.assertEqual(wizard.pdp_identifier, '944716448')
        with mock_pdp_registration():
            wizard.button_register_pdp_participant()
        self.assertRecordValues(self.env.company, [{
            'pdp_identifier': '944716448',
            'routing_identifier': '0225:944716448',
        }])

    def test_pdp_create_participant_invalid_identifier(self):
        # Registering a participant with an invalid identifier should raise an error
        wizard = self.env['pdp.registration'].create({
            'pdp_identifier': 'abc',
            'contact_email': 'yourcompany@test.example.com',
        })
        with self.assertRaisesRegex(UserError, "The Identifier is not valid. The expected format is: SIREN, SIREN_SIRET, SIREN_SIRET_CodeRoutage or SIREN_SuffixeAdressage"):
            wizard.button_register_pdp_participant()

    def test_pdp_create_participant_missing_data(self):
        # creating a participant without identifier should not be possible
        wizard = self.env['pdp.registration'].create({
            'pdp_identifier': '944716448',
            'contact_email': False,
        })
        with self.assertRaisesRegex(ValidationError, "The contact email is required."):
            wizard.button_register_pdp_participant()

        wizard = self.env['pdp.registration'].create({
            'pdp_identifier': False,
            'contact_email': 'yourcompany@test.example.com',
        })
        with self.assertRaisesRegex(UserError, "The Identifier is required."):
            wizard.button_register_pdp_participant()

    def test_pdp_create_participant_change_identifier(self):
        # Updating the identifier in the wizard should
        #  - Update the company `pdp_identifier`
        #  - Register the company with that value
        company = self.env.company
        self.env.company.partner_id.write({
            'routing_identifier': '0225:552008443',
        })
        wizard = self.env['pdp.registration'].create({})
        self.assertEqual(wizard.pdp_identifier, '552008443')
        wizard.write({
            'pdp_identifier': '944716448',
            'contact_email': 'yourcompany@test.example.com',
        })
        with mock_pdp_registration():
            wizard.button_register_pdp_participant()
        self.assertRecordValues(company, [{
            'account_peppol_proxy_state': 'smp_registration',
            'pdp_identifier': '944716448',
            'routing_identifier': '0225:944716448',
        }])

    def test_pdp_create_participant_receiver(self):
        company = self.env.company
        self.assertEqual(company.pdp_identifier, '968515759_96851575905899')
        wizard = self.env['pdp.registration'].create({
            'pdp_identifier': '944716448',
            'contact_email': 'yourcompany@test.example.com',
        })
        with mock_pdp_registration(peppol_state='receiver'):
            wizard.button_register_pdp_participant()
            self.assertRecordValues(company, [{
                'account_peppol_proxy_state': 'smp_registration',
                'pdp_identifier': '944716448',
                'routing_identifier': '0225:944716448',
            }])

            # The participant should be automatically registered as receiver after some time
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(self.env.company.account_peppol_proxy_state, 'receiver')

    def test_pdp_create_reject_participant(self):
        # the account_peppol_proxy_state should change to rejected
        # if we reject the participant
        company = self.env.company
        wizard = self.env['pdp.registration'].create(self._get_participant_vals())

        with mock_pdp_registration(peppol_state='rejected'):
            wizard.button_register_pdp_participant()
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(company.account_peppol_proxy_state, 'rejected')

    def test_pdp_create_duplicate_participant(self):
        """ If you create a duplicate participant, it will take over the previous one"""
        with mock_pdp_registration(peppol_state='receiver'):
            wizard = self.env['pdp.registration'].create(self._get_participant_vals())
            wizard.button_register_pdp_participant()

            wizard.company_id.account_peppol_proxy_state = 'not_registered'
            wizard.account_peppol_proxy_state = 'not_registered'
            wizard.button_register_pdp_participant()
            self.assertEqual(self.env.company.account_peppol_proxy_state, 'smp_registration')

            # The participant is still a receiver on IAP
            self.env['account_edi_proxy_client.user']._cron_peppol_get_participant_status()
            self.assertEqual(self.env.company.account_peppol_proxy_state, 'receiver')

    def test_peppol_pdp_unqiue_constraint(self):
        """Test that we can either have a PDP or a Peppol user per company (and per edi mode)"""
        self.assertRecordValues(self.proxy_user, [{
            'active': True,
            'company_id': self.env.company.id,
            'proxy_type': 'pdp',
            'edi_mode': 'test',
        }])

        with self.assertRaises(Exception), mute_logger('odoo.sql_db'):
            self.env['account_edi_proxy_client.user'].create([{
                'active': True,
                'id_client': 'client-demo',
                'company_id': self.env.company.id,
                'edi_identification': 'client-demo',
                'private_key_id': self.env['certificate.key'].sudo()._generate_rsa_private_key(self.env.company).id,
                'refresh_token': False,
                'proxy_type': 'pdp',
                'edi_mode': 'test',
            }])

        with self.assertRaises(Exception), mute_logger('odoo.sql_db'):
            self.env['account_edi_proxy_client.user'].create([{
                'active': True,
                'id_client': 'client-demo',
                'company_id': self.env.company.id,
                'edi_identification': 'client-demo',
                'private_key_id': self.env['certificate.key'].sudo()._generate_rsa_private_key(self.env.company).id,
                'refresh_token': False,
                'proxy_type': 'peppol',
                'edi_mode': 'test',
            }])

        other_company = self.setup_other_company(name='other')['company']
        other_pdp_user = self.env['account_edi_proxy_client.user'].create([{
            'active': True,
            'id_client': 'client-demo-pdp',
            'company_id': other_company.id,
            'edi_identification': 'client-demo',
            'private_key_id': self.env['certificate.key'].sudo()._generate_rsa_private_key(self.env.company).id,
            'refresh_token': False,
            'proxy_type': 'pdp',
            'edi_mode': 'test',
        }])
        self.assertTrue(other_pdp_user)

        other2_company = self.setup_other_company(name='other2')['company']
        other2_peppol_user = self.env['account_edi_proxy_client.user'].create([{
            'active': True,
            'id_client': 'client-demo-peppol',
            'company_id': other2_company.id,
            'edi_identification': 'client-demo',
            'private_key_id': self.env['certificate.key'].sudo()._generate_rsa_private_key(self.env.company).id,
            'refresh_token': False,
            'proxy_type': 'peppol',
            'edi_mode': 'test',
        }])
        self.assertTrue(other2_peppol_user)
