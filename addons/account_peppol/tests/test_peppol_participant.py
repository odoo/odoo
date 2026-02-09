from base64 import b64encode

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged, freeze_time
from odoo.tools.misc import file_open

from odoo.addons.account_peppol.tests.common import PeppolConnectorCommon


@freeze_time('2023-01-01')
@tagged('-at_install', 'post_install')
class TestPeppolParticipant(PeppolConnectorCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.private_key = cls.env['certificate.key'].create([{
            'name': 'Test key PEPPOL',
            'content': b64encode(file_open('account_peppol/tests/assets/private_key.pem', 'rb').read()),
        }])

        cls.env.company.write({
            'peppol_eas': '0208',
            'peppol_endpoint': '0239843188',
            'account_peppol_phone_number': '+32483123456',
            'account_peppol_contact_email': 'yourcompany@test.example.com',
        })

    def test_ignore_archived_edi_users(self):
        with self._mock_requests([
            self._mock_can_connect(),
            self._mock_connect(peppol_state='sender'),
        ]):
            wizard = self.env['peppol.registration'].create({})
            wizard.button_register_peppol_participant()

        self.env['account_edi_proxy_client.user'].create([{
            'active': False,
            'id_client': 'client-demo',
            'company_id': self.env.company.id,
            'edi_identification': 'client-demo',
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
        with self.assertRaises(ValidationError):
            wizard.button_register_peppol_participant()

    def test_register_participant_for_the_first_time_as_sender_then_receiver_then_unregister(self):
        # Register the use for the very first time as sender.
        with self._mock_requests([
            self._mock_can_connect(),
            self._mock_connect(peppol_state='sender'),
            self._mock_lookup_participant(already_exists=True),
        ]):
            wizard = self.env['peppol.registration'].create({})
            self.assertRecordValues(wizard, [{'smp_registration': False}])
            wizard.button_register_peppol_participant()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'sender'}])

        # sender -> receiver.
        settings = self.env['res.config.settings'].create({})
        with self._mock_requests([
            self._mock_lookup_participant(),
            self._mock_register_sender_as_receiver(),
            self._mock_participant_status('receiver'),
        ]):
            settings.button_peppol_register_sender_as_receiver()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'receiver'}])

        # receiver -> not_registered.
        with self._mock_requests([
            self._mock_participant_status('receiver'),
            self._mock_get_all_documents(),
            self._mock_cancel_peppol_registration(),
        ]):
            config_wizard = self.env['peppol.config.wizard'].create({})
            config_wizard.button_peppol_unregister()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'not_registered'}])

    def test_register_participant_already_exists_on_peppol_as_sender(self):
        with self._mock_requests([
            self._mock_can_connect(),
            self._mock_connect(peppol_state='sender'),
            self._mock_lookup_participant(),
        ]):
            wizard = self.env['peppol.registration'].create({})
            self.assertRecordValues(wizard, [{'smp_registration': True}])
            wizard.button_register_peppol_participant()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'sender'}])

    def test_register_participant_already_exists_on_peppol_as_receiver(self):
        with self._mock_requests([
            self._mock_can_connect(),
            self._mock_connect(peppol_state='sender'),
            self._mock_lookup_participant(already_exists=True),
        ]):
            wizard = self.env['peppol.registration'].create({})
            self.assertRecordValues(wizard, [{'smp_registration': False}])
            wizard.button_register_peppol_participant()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'sender'}])

    def test_register_participant_rejected(self):
        with (
            self._mock_requests([
                self._mock_can_connect(),
                self._mock_connect(peppol_state='rejected'),
                self._mock_lookup_participant(),
            ]),
            self.assertRaisesRegex(UserError, "There was an issue with the Peppol Participant"),
        ):
            wizard = self.env['peppol.registration'].create({})
            self.assertRecordValues(wizard, [{'smp_registration': True}])
            wizard.button_register_peppol_participant()
        self.assertRecordValues(self.env.company, [{'account_peppol_proxy_state': 'not_registered'}])

    def test_config_update_email(self):
        with self._mock_requests([
            self._mock_can_connect(),
            self._mock_connect(peppol_state='sender'),
        ]):
            wizard = self.env['peppol.registration'].create({})
            wizard.button_register_peppol_participant()
        self.assertRecordValues(self.env.company, [{
            'account_peppol_proxy_state': 'sender',
            'account_peppol_contact_email': 'yourcompany@test.example.com',
        }])

        # Change the email.
        config_wizard = self.env['peppol.config.wizard'].create({'account_peppol_contact_email': 'another@email.be'})
        with self._mock_requests([self._mock_update_user()]) as mocks_results:
            config_wizard.button_sync_form_with_peppol_proxy()
            self.assertEqual(
                mocks_results['called']['https://peppol.test.odoo.com/api/peppol/1/update_user']['kwargs']['json']['params']['update_data']['peppol_contact_email'],
                'another@email.be',
            )

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
            'display_use_parent_connection_selection': True,
            'use_parent_connection_selection': 'use_self',
        }])

        wizard.write({
            'contact_email': "turlututu@tsointsoin",
            'phone_number': "+3236656565",
            'peppol_eas': '0208',
            'peppol_endpoint': '0239843188',
        })

        # You can't register the branch using the same EAS/Endpoint than the parent company.
        with self.assertRaises(ValidationError):
            wizard.button_register_peppol_participant()

        wizard.peppol_endpoint = '0477472701'
        with self._mock_requests([
            self._mock_can_connect(),
            self._mock_connect(peppol_state='sender'),
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
            config_wizard = self.env['peppol.config.wizard'].with_context(allowed_company_ids=branch.ids).create({})
            config_wizard.button_peppol_unregister()
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
            'display_use_parent_connection_selection': True,
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
            'display_use_parent_connection_selection': True,
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
            'display_use_parent_connection_selection': False,
            'use_parent_connection_selection': 'use_self',
        }])
        with self._mock_requests([
            self._mock_can_connect(),
            self._mock_connect(peppol_state='receiver'),
        ]):
            wizard.button_register_peppol_participant()

        settings = self.env['res.config.settings'].with_context(allowed_company_ids=self.env.company.ids).create({})
        self.assertRecordValues(settings, [{
            'account_peppol_proxy_state': 'receiver',
            'peppol_use_parent_company': False,
        }])

        # Back to the branch.
        wizard = self.env['peppol.registration'].with_context(allowed_company_ids=branch.ids).create({})
        self.assertRecordValues(wizard, [{
            'company_id': branch.id,
            'parent_company_id': self.env.company.id,
            'selected_company_id': self.env.company.id,
            'display_use_parent_connection_selection': True,
            'use_parent_connection_selection': 'use_parent',
            'peppol_eas': self.env.company.peppol_eas,
            'peppol_endpoint': self.env.company.peppol_endpoint,
            'phone_number': self.env.company.account_peppol_phone_number,
            'contact_email': self.env.company.account_peppol_contact_email,
        }])
        with self._mock_requests([
            self._mock_can_connect(),
            self._mock_connect(peppol_state='sender', id_client='test_id_client_branch'),
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
            config_wizard = self.env['peppol.config.wizard'].with_context(allowed_company_ids=branch.ids).create({})
            config_wizard.button_peppol_unregister()
        self.assertRecordValues(settings, [{
            'account_peppol_proxy_state': 'not_registered',
            'peppol_use_parent_company': False,
        }])

        # Back to the initial state.
        wizard = self.env['peppol.registration'].with_context(allowed_company_ids=branch.ids).create({})
        self.assertRecordValues(wizard, [{
            'company_id': branch.id,
            'parent_company_id': self.env.company.id,
            'selected_company_id': self.env.company.id,
            'display_use_parent_connection_selection': True,
            'use_parent_connection_selection': 'use_parent',
            'peppol_eas': self.env.company.peppol_eas,
            'peppol_endpoint': self.env.company.peppol_endpoint,
            'phone_number': self.env.company.account_peppol_phone_number,
            'contact_email': self.env.company.account_peppol_contact_email,
        }])

    def test_deregister_with_client_gone_error(self):
        """Test deregistration succeeds even when proxy returns client_gone error"""
        with self._mock_requests([
            self._mock_can_connect(),
            self._mock_lookup_participant(),
            self._mock_connect(peppol_state='smp_registration'),
        ]):
            wizard = self.env['peppol.registration'].create({})
            self.assertTrue(wizard.smp_registration)
            wizard.button_register_peppol_participant()
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'smp_registration')

        config_wizard = self.env['peppol.config.wizard'].create({})
        with self._mock_requests([
            self._mock_participant_status('smp_registration', exists=False)
        ]):
            config_wizard.button_peppol_unregister()

        # Should successfully deregister despite Exception
        self.assertEqual(self.env.company.account_peppol_proxy_state, 'not_registered')
