from base64 import b64encode

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged, TransactionCase, freeze_time
from odoo.tools import mute_logger
from odoo.tools.misc import file_open

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

        cls.env.company.write({
            'peppol_eas': '0208',
            'peppol_endpoint': '0239843188',
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
            wizard.button_peppol_sender_registration()

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

        # sender -> smp_registration.
        settings = self.env['res.config.settings'].create({})
        with self._mock_requests([
            self._mock_lookup_participant(),
            self._mock_register_sender_as_receiver(),
        ]):
            settings.button_peppol_smp_registration()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'smp_registration'}])

        # smp_registration -> receiver.
        with self._mock_requests([self._mock_participant_status('receiver')]):
            self.env.company.account_edi_proxy_client_ids._peppol_get_participant_status()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'receiver'}])

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

    def test_peppol_registration_register_as_self(self):
        self.env.company.write({'child_ids': [Command.create({'name': 'Branch A'})]})
        branch = self.env.company.child_ids

        settings = self.env['res.config.settings'].with_context(allowed_company_ids=branch.ids).create({})
        self.assertRecordValues(settings, [{
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
            'contact_email': "turlututu@tsointsoin",
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
            'account_peppol_contact_email': "turlututu@tsointsoin",
            'account_peppol_phone_number': "+3236656565",
        }])

        settings = self.env['res.config.settings'].with_context(allowed_company_ids=branch.ids).create({})
        self.assertRecordValues(settings, [{
            'account_peppol_proxy_state': 'sender',
            'peppol_use_parent_company': False,
        }])

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

        settings = self.env['res.config.settings'].create({})
        with self._mock_requests([
            self._mock_participant_status('sender', exists=False)
        ]):
            settings.button_deregister_peppol_participant()

        # Should successfully deregister despite Exception
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'not_registered')
