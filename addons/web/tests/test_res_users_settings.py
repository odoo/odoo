from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestResUsersSettings(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env['res.users'].create({
            'name': 'Jean',
            'login': 'jean@mail.com',
            'password': 'jean@mail.com',
        })
        cls.user_settings = cls.env['res.users.settings']._find_or_create_for_user(cls.user)
        cls.window_action = cls.env['ir.actions.act_window'].create({
            'name': 'Test Action',
            'res_model': 'res.users',
        })

    def test_fields_validity_embedded_action_settings(self):
        '''
        Test that the embedded actions fields 'embedded_actions_order' and 'embedded_actions_visibility' are valid
        and raise ValidationError when necessary.
        '''
        embedded_action_settings_data = {
            'user_setting_id': self.user_settings.id,
            'action_id': self.window_action.id,
            'res_model': 'res.users',
            'res_id': self.user.id,
            'embedded_visibility': True,
        }

        # Invalid case: duplicated ids
        embedded_action_settings_data.update({
            'embedded_actions_order': '1,2,1',
            'embedded_actions_visibility': '3,3,4',
        })
        with self.assertRaises(ValidationError, msg='The ids in embedded_actions_order must not be duplicated'):
            self.env['res.users.settings.embedded.action'].create(embedded_action_settings_data)

        # Invalid case: non-integer ids or non-false values
        embedded_action_settings_data.update({
            'embedded_actions_order': '1,2,true',
            'embedded_actions_visibility': '3,4,false,abc',
        })
        with self.assertRaises(ValidationError, msg='The ids in embedded_actions_order must only be integers or "false"'):
            self.env['res.users.settings.embedded.action'].create(embedded_action_settings_data)

    def test_set_and_get_embedded_action_settings(self):
        '''
        Test setting and getting embedded action settings.
        '''
        settings_vals = {
            'embedded_actions_order': [False, 1, 2, 3],
            'embedded_actions_visibility': [2, False, 3],
            'embedded_visibility': True,
        }
        self.user_settings.set_embedded_actions_setting(
            action_id=self.window_action.id,
            res_id=self.user.id,
            vals={
                **settings_vals,
                'res_model': 'res.users',
            },
        )
        # Check if the setting is correctly created
        embedded_actions_config = self.user_settings.embedded_actions_config_ids
        self.assertEqual(len(embedded_actions_config), 1, 'There should be one embedded action setting created.')
        self.assertEqual(embedded_actions_config.action_id, self.window_action, 'The action should match the one set.')
        self.assertEqual(embedded_actions_config.res_id, self.user.id, 'The res_id should match the one set.')
        self.assertEqual(embedded_actions_config.res_model, 'res.users', 'The res_model should match the one set.')
        self.assertEqual(embedded_actions_config.embedded_actions_order, 'false,1,2,3', 'The embedded actions order should match the one set.')
        self.assertEqual(embedded_actions_config.embedded_actions_visibility, '2,false,3', 'The embedded actions visibility should match the one set.')
        self.assertEqual(embedded_actions_config.embedded_visibility, True, 'The embedded visibility should be True.')
        # Check if the settings are correctly formatted from the getter
        embedded_settings = self.user_settings.get_embedded_actions_settings()
        expected_settings = {
            f'{self.window_action.id}+{self.user.id}': settings_vals,
        }
        self.assertEqual(embedded_settings, expected_settings, 'The settings should be correctly formatted with the given values.')

        # Edit the settings
        new_settings_vals = {
            'embedded_actions_order': [3, 1, False, 2],
            'embedded_actions_visibility': [1, 3],
            'embedded_visibility': False,
        }
        self.user_settings.set_embedded_actions_setting(
            action_id=self.window_action.id,
            res_id=self.user.id,
            vals=new_settings_vals,
        )
        # Check if the setting is correctly updated
        embedded_actions_config = self.user_settings.embedded_actions_config_ids
        self.assertEqual(len(embedded_actions_config), 1, 'There should still be one embedded action setting after update.')
        self.assertEqual(embedded_actions_config.action_id, self.window_action, 'The action should remain the same after update.')
        self.assertEqual(embedded_actions_config.res_id, self.user.id, 'The res_id should remain the same after update.')
        self.assertEqual(embedded_actions_config.res_model, 'res.users', 'The res_model should remain the same after update.')
        self.assertEqual(embedded_actions_config.embedded_actions_order, '3,1,false,2', 'The embedded actions order should be updated.')
        self.assertEqual(embedded_actions_config.embedded_actions_visibility, '1,3', 'The embedded actions visibility should be updated.')
        self.assertEqual(embedded_actions_config.embedded_visibility, False, 'The embedded visibility should be updated to False.')
        # Check if the settings are correctly formatted after the update
        embedded_settings = self.user_settings.get_embedded_actions_settings()
        expected_settings = {
            f'{self.window_action.id}+{self.user.id}': new_settings_vals,
        }
        self.assertEqual(embedded_settings, expected_settings, 'The settings should be correctly formatted after the update with the new values.')
