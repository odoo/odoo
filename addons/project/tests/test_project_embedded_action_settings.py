from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestProjectEmbeddedActionSettings(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'password': 'test_password',
        })
        cls.user_settings = cls.env['res.users.settings']._find_or_create_for_user(cls.user)
        cls.window_action = cls.env['ir.actions.act_window'].create({
            'name': 'Test Action',
            'res_model': 'project.project',
        })
        cls.embedded_action_1, cls.embedded_action_2 = cls.env['ir.embedded.actions'].create([
            {
                'name': 'Embedded Action 1',
                'parent_res_model': 'project.project',
                'parent_action_id': cls.window_action.id,
                'action_id': cls.window_action.id,
            },
            {
                'name': 'Embedded Action 2',
                'parent_res_model': 'project.project',
                'parent_action_id': cls.window_action.id,
                'action_id': cls.window_action.id,
            },
        ])
        cls.embedded_action_settings = cls.env['res.users.settings.embedded.action'].create({
            'user_setting_id': cls.user_settings.id,
            'action_id': cls.window_action.id,
            'res_model': 'project.project',
            'res_id': cls.project_goats.id,
            'embedded_actions_order': f'{cls.embedded_action_2.id},false,{cls.embedded_action_1.id}',
            'embedded_actions_visibility': f'{cls.embedded_action_1.id},{cls.embedded_action_2.id}',
            'embedded_visibility': True,
        })

    def test_copy_embedded_action_settings(self):
        '''
        Test that embedded action settings are copied correctly when a project is copied.
        '''
        copied_project = self.project_goats.copy()
        # Check if the embedded action settings are copied
        copied_settings = self.env['res.users.settings.embedded.action'].search([
            ('user_setting_id', '=', self.user_settings.id),
            ('action_id', '=', self.window_action.id),
            ('res_id', '=', copied_project.id),
        ])
        self.assertEqual(len(copied_settings), 1, 'There should be one embedded action setting for the copied project.')
        self.assertEqual(len(self.user_settings.embedded_actions_config_ids), 2, 'There should be two embedded action settings after copying the project.')
        self.assertEqual(copied_settings.action_id, self.embedded_action_settings.action_id, 'The action_id should match the original.')
        self.assertEqual(copied_settings.res_id, copied_project.id, 'The res_id should match the copied project id.')
        self.assertEqual(copied_settings.res_model, self.embedded_action_settings.res_model, 'The res_model should match the original.')
        self.assertEqual(copied_settings.embedded_actions_order, self.embedded_action_settings.embedded_actions_order, 'The embedded actions order should match the original.')
        self.assertEqual(copied_settings.embedded_actions_visibility, self.embedded_action_settings.embedded_actions_visibility, 'The embedded actions visibility should match the original.')
        self.assertEqual(copied_settings.embedded_visibility, self.embedded_action_settings.embedded_visibility, 'The embedded visibility should match the original.')

    def test_copy_custom_embedded_action_settings(self):
        '''
        Test that the user-specific actions are not copied in the settings when a project is copied.
        '''
        # Create user-specific and shared embedded actions
        user_specific_embedded_action, shared_embedded_action = self.env['ir.embedded.actions'].create([
            {
                'name': 'Custom User-Specific Action',
                'parent_res_model': 'project.project',
                'parent_action_id': self.window_action.id,
                'action_id': self.window_action.id,
                'parent_res_id': self.project_pigs.id,
                'user_id': self.user.id,  # User-specific action
            },
            {
                'name': 'Custom Shared Action',
                'parent_res_model': 'project.project',
                'parent_action_id': self.window_action.id,
                'action_id': self.window_action.id,
                'parent_res_id': self.project_pigs.id,
                'user_id': False,  # Shared action
            },
        ])
        # Create settings containing those embedded actions
        self.env['res.users.settings.embedded.action'].create({
            'user_setting_id': self.user_settings.id,
            'action_id': self.window_action.id,
            'res_model': 'project.project',
            'res_id': self.project_pigs.id,
            'embedded_actions_order': f'{shared_embedded_action.id},{user_specific_embedded_action.id}',
            'embedded_actions_visibility': f'{user_specific_embedded_action.id},{shared_embedded_action.id}',
            'embedded_visibility': True,
        })
        # Copy the project
        copied_project = self.project_pigs.copy()
        # Get the copied shared embedded action
        copied_shared_embedded_action = self.env['ir.embedded.actions'].search([
            ('parent_res_model', '=', 'project.project'),
            ('parent_res_id', '=', copied_project.id),
            ('user_id', '=', False)  # Ensure it's a shared action
        ], limit=1)
        # Check if the shared embedded action settings are correctly copied
        copied_settings = self.env['res.users.settings.embedded.action'].search([
            ('user_setting_id', '=', self.user_settings.id),
            ('action_id', '=', self.window_action.id),
            ('res_id', '=', copied_project.id),
        ])
        self.assertEqual(len(copied_settings), 1, 'There should be one embedded action setting for the copied project.')
        self.assertEqual(len(self.user_settings.embedded_actions_config_ids), 3, 'There should be three embedded action settings after copying the project.')
        self.assertEqual(copied_settings.action_id, self.embedded_action_settings.action_id, 'The action_id should match the original.')
        self.assertEqual(copied_settings.res_id, copied_project.id, 'The res_id should match the copied project id.')
        self.assertEqual(copied_settings.res_model, self.embedded_action_settings.res_model, 'The res_model should match the original.')
        self.assertEqual(copied_settings.embedded_actions_order, str(copied_shared_embedded_action.id), 'Only the shared embedded action should be copied in the actions order.')
        self.assertEqual(copied_settings.embedded_actions_visibility, str(copied_shared_embedded_action.id), 'Only the shared embedded action should be copied in the visible actions.')
        self.assertEqual(copied_settings.embedded_visibility, self.embedded_action_settings.embedded_visibility, 'The embedded visibility should match the original.')

    def test_unlink_project_removes_embedded_action_settings(self):
        '''
        Test that unlinking a project removes the embedded action settings associated with it.
        '''
        self.assertTrue(self.embedded_action_settings.exists(), 'The embedded action settings should exist before unlinking the project.')
        self.project_goats.unlink()
        # Check if the embedded action settings are removed
        self.assertFalse(self.embedded_action_settings.exists(), 'The embedded action settings should be removed when the project is unlinked.')
        remaining_settings = self.env['res.users.settings.embedded.action'].search([
            ('user_setting_id', '=', self.user_settings.id),
            ('action_id', '=', self.window_action.id),
            ('res_id', '=', self.project_goats.id),
        ])
        self.assertEqual(len(remaining_settings), 0, 'There should be no more embedded action settings for the unlinked project.')
